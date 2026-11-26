# As Above, So Below. As Within, So Without.
# The Future Dictates the Past and the Past is Always Present.

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
PACK_DIR = ROOT / "pathfinder_god_hd"
RAW_DIR = PACK_DIR / "raw"
TOKEN_DIR = PACK_DIR / "tokens"
UI_DIR = PACK_DIR / "ui"
MANIFEST_PATH = PACK_DIR / "pack_manifest.json"

TOKEN_SIZE = 256
TOKEN_NAMES = [
    "hero_occult_investigator",
    "hero_eldritch_scholar",
    "hero_lantern_warden",
    "hero_void_ranger",
    "monster_star_spawn",
    "monster_shoggoth",
    "monster_void_cultist",
    "monster_astral_hound",
]


def chroma_key_and_despill(img: Image.Image) -> Image.Image:
    rgba = np.array(img.convert("RGBA"), dtype=np.float32)
    r, g, b = rgba[:, :, 0], rgba[:, :, 1], rgba[:, :, 2]

    magenta_score = np.minimum(r, b) - g
    is_bg = (magenta_score > 70.0) & (r > 130.0) & (b > 130.0) & (g < 140.0)
    is_fringe = (~is_bg) & (magenta_score > 20.0) & (r > 100.0) & (b > 100.0)

    alpha = np.where(is_bg, 0.0, 255.0)
    alpha = np.where(is_fringe, np.clip(255.0 - (magenta_score - 20.0) * 4.5, 0.0, 255.0), alpha)

    despill_cap = np.maximum(g, np.minimum(r, b) * 0.55)
    r = np.where(is_fringe, np.minimum(r, despill_cap), r)
    b = np.where(is_fringe, np.minimum(b, despill_cap), b)

    out = np.stack([r, g, b, alpha], axis=-1)
    out[alpha == 0.0, :3] = 0.0
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), mode="RGBA")


def slice_tokens(raw_path: Path) -> list[str]:
    sheet = chroma_key_and_despill(Image.open(raw_path))
    w, h = sheet.size
    cw, ch = w / 4.0, h / 2.0
    margin = 4
    target = TOKEN_SIZE - margin * 2
    written: list[str] = []

    for idx, name in enumerate(TOKEN_NAMES):
        row = idx // 4
        col = idx % 4
        cell = sheet.crop(
            (
                int(round(col * cw)),
                int(round(row * ch)),
                int(round((col + 1) * cw)),
                int(round((row + 1) * ch)),
            )
        )
        bbox = cell.getbbox()
        if bbox is None:
            continue
        cropped = cell.crop(bbox)
        scale = min(target / cropped.width, target / cropped.height)
        nw = max(1, int(round(cropped.width * scale)))
        nh = max(1, int(round(cropped.height * scale)))
        resized = cropped.resize((nw, nh), Image.Resampling.LANCZOS)

        out = Image.new("RGBA", (TOKEN_SIZE, TOKEN_SIZE), (0, 0, 0, 0))
        out.alpha_composite(resized, ((TOKEN_SIZE - nw) // 2, (TOKEN_SIZE - nh) // 2))
        out_path = TOKEN_DIR / f"{name}.png"
        out.save(out_path)
        written.append(f"tokens/{name}.png")
        print(f"TOKEN: {name} -> {TOKEN_SIZE}x{TOKEN_SIZE}")
    return written


def extract_ui_components(raw_path: Path) -> list[str]:
    keyed = chroma_key_and_despill(Image.open(raw_path))
    atlas_path = UI_DIR / "eldritch_hud_sheet.png"
    keyed.save(atlas_path)
    written = ["ui/eldritch_hud_sheet.png"]

    alpha = np.array(keyed)[:, :, 3]
    ds = 4
    small = alpha[::ds, ::ds] > 24
    sh, sw = small.shape
    visited = np.zeros((sh, sw), dtype=bool)
    boxes: list[tuple[int, int, int, int]] = []

    for y in range(sh):
        for x in range(sw):
            if not small[y, x] or visited[y, x]:
                continue
            q: deque[tuple[int, int]] = deque([(y, x)])
            visited[y, x] = True
            min_y = max_y = y
            min_x = max_x = x
            count = 0
            while q:
                cy, cx = q.popleft()
                count += 1
                if cy < min_y:
                    min_y = cy
                if cy > max_y:
                    max_y = cy
                if cx < min_x:
                    min_x = cx
                if cx > max_x:
                    max_x = cx
                for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                    if 0 <= ny < sh and 0 <= nx < sw and small[ny, nx] and not visited[ny, nx]:
                        visited[ny, nx] = True
                        q.append((ny, nx))
            if count >= 40:
                x0 = max(0, min_x * ds - 4)
                y0 = max(0, min_y * ds - 4)
                x1 = min(keyed.width, (max_x + 1) * ds + 4)
                y1 = min(keyed.height, (max_y + 1) * ds + 4)
                boxes.append((x0, y0, x1, y1))

    boxes.sort(key=lambda b: (b[1] // 120, b[0]))
    for idx, box in enumerate(boxes, start=1):
        piece = keyed.crop(box)
        tb = piece.getbbox()
        if tb is None:
            continue
        piece = piece.crop(tb)
        fname = f"hud_piece_{idx:02d}.png"
        piece.save(UI_DIR / fname)
        written.append(f"ui/{fname}")
        print(f"UI: {fname} -> {piece.width}x{piece.height}")
    return written


def main() -> int:
    TOKEN_DIR.mkdir(parents=True, exist_ok=True)
    UI_DIR.mkdir(parents=True, exist_ok=True)

    tokens_raw = RAW_DIR / "tokens_raw.jpg"
    hud_raw = RAW_DIR / "hud_ui_raw.jpg"
    if not tokens_raw.exists() or not hud_raw.exists():
        print(f"MISSING RAW INPUTS IN: {RAW_DIR}", file=sys.stderr)
        return 1

    token_files = slice_tokens(tokens_raw)
    ui_files = extract_ui_components(hud_raw)

    manifest = {
        "pack": "pathfinder_god_hd",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tokens": token_files,
        "ui": ui_files,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"UPDATED: {MANIFEST_PATH} ({len(token_files)} tokens, {len(ui_files)} UI assets)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
