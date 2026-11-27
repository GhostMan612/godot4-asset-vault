#!/usr/bin/env python3
# ============================================================
# As Above, So Below. As Within, So Without.
# The Future Dictates the Past and the Past is Always Present.
# ============================================================
import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "vendor" / "cc0_topdown"
THEMES = ROOT / "themes"
THEME_IDS = ["tactical_compound", "moonbase_lab", "industrial_warehouse", "bank_vault", "ancestral_crypt"]


def normal_from_albedo(img: Image.Image) -> Image.Image:
    gray = img.convert("L")
    w, h = gray.size
    src = gray.load()
    out = Image.new("RGBA", (w, h), (128, 128, 255, 255))
    dst = out.load()
    for y in range(h):
        for x in range(w):
            l = src[max(0, x - 1), y]
            r = src[min(w - 1, x + 1), y]
            u = src[x, max(0, y - 1)]
            d = src[x, min(h - 1, y + 1)]
            nx = max(0, min(255, 128 + (l - r) * 2))
            ny = max(0, min(255, 128 + (u - d) * 2))
            dst[x, y] = (nx, ny, 255, 255)
    return out


def available_sources() -> list:
    if not SOURCES.exists():
        return []
    return [p for p in SOURCES.rglob("*.png") if p.stat().st_size > 1024]


def pack(theme_id: str, sources: list) -> bool:
    if not sources:
        return False
    d = THEMES / theme_id
    sheet = Image.new("RGBA", (256, 64), (0, 0, 0, 255))
    draw = ImageDraw.Draw(sheet)
    for i in range(4):
        src = Image.open(sources[i % len(sources)]).convert("RGBA").resize((64, 64), Image.Resampling.NEAREST)
        sheet.paste(src, (i * 64, 0), src)
        draw.rectangle((i * 64, 0, i * 64 + 63, 63), outline=(60, 70, 80, 255), width=1)
    sheet.save(d / "floor_atlas.png")
    normal_from_albedo(sheet).save(d / "floor_atlas_n.png")
    meta_path = d / "theme_meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["provenance"] = "CC0_CURATED"
    meta["credit"] = "; ".join(p.name for p in sources[:4])
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return True


if __name__ == "__main__":
    sources = available_sources()
    if not sources:
        print("NO VERIFIED CC0 SOURCES in vendor/cc0_topdown — keeping ORIGINAL_PROCEDURAL atlases")
    else:
        for theme_id in THEME_IDS:
            print(theme_id, "CC0_SWAPPED" if pack(theme_id, sources) else "SKIPPED")
