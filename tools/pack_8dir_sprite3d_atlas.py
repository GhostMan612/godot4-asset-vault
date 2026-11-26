# As Above, So Below. As Within, So Without.
# The Future Dictates the Past and the Past is Always Present.

from pathlib import Path
import sys
import numpy as np
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
PACK_DIR = ROOT / "tacplanshooter_hd"
RAW_DIR = PACK_DIR / "raw"
OUT_SPRITES = PACK_DIR / "sprites" / "units_8dir"
OUT_RES = PACK_DIR / "resources" / "units_8dir"

CELL_SIZE = 256
COLS = 4
ROWS = 2
BORDER_INSET = 8

UNITS = [
    (
        "operative_carbine",
        "operative_8dir_raw.jpg",
        [
            (0, 0, False),
            (1, 3, True),
            (0, 2, False),
            (0, 3, False),
            (1, 0, False),
            (0, 3, True),
            (1, 2, False),
            (1, 3, False),
        ],
    ),
    (
        "opfor_enforcer",
        "opfor_enforcer_8dir_raw.jpg",
        [
            (0, 0, False),
            (1, 3, True),
            (0, 2, True),
            (0, 3, False),
            (1, 0, False),
            (0, 3, True),
            (0, 2, False),
            (1, 3, False),
        ],
    ),
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


def pack_8dir_sheet(raw_img: Image.Image, mapping: list[tuple[int, int, bool]]) -> Image.Image:
    w, h = raw_img.size
    src_cw = w / COLS
    src_ch = h / ROWS
    canvas = Image.new("RGBA", (CELL_SIZE * COLS, CELL_SIZE * ROWS), (0, 0, 0, 0))
    margin = 10
    target_box = CELL_SIZE - margin * 2

    for idx, (src_row, src_col, flip_x) in enumerate(mapping):
        x0 = int(round(src_col * src_cw)) + BORDER_INSET
        y0 = int(round(src_row * src_ch)) + BORDER_INSET
        x1 = int(round((src_col + 1) * src_cw)) - BORDER_INSET
        y1 = int(round((src_row + 1) * src_ch)) - BORDER_INSET

        cell = chroma_key_and_despill(raw_img.crop((x0, y0, x1, y1)))
        if flip_x:
            cell = ImageOps.mirror(cell)

        bbox = cell.getbbox()
        if bbox is None:
            continue
        cropped = cell.crop(bbox)
        scale = min(target_box / cropped.width, target_box / cropped.height)
        new_w = max(1, int(round(cropped.width * scale)))
        new_h = max(1, int(round(cropped.height * scale)))
        resized = cropped.resize((new_w, new_h), Image.Resampling.NEAREST)

        dst_row = idx // COLS
        dst_col = idx % COLS
        dest_x = dst_col * CELL_SIZE + (CELL_SIZE - new_w) // 2
        dest_y = dst_row * CELL_SIZE + (CELL_SIZE - margin - new_h)
        canvas.alpha_composite(resized, (dest_x, dest_y))
    return canvas


def build_normal_and_specular(rgba_img: Image.Image) -> tuple[Image.Image, Image.Image]:
    arr = np.array(rgba_img, dtype=np.float32) / 255.0
    alpha = arr[:, :, 3]
    lum = (0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]) * alpha

    pad = np.pad(lum, 1, mode="edge")
    gx = (
        (pad[:-2, 2:] + 2.0 * pad[1:-1, 2:] + pad[2:, 2:])
        - (pad[:-2, :-2] + 2.0 * pad[1:-1, :-2] + pad[2:, :-2])
    )
    gy = (
        (pad[2:, :-2] + 2.0 * pad[2:, 1:-1] + pad[2:, 2:])
        - (pad[:-2, :-2] + 2.0 * pad[:-2, 1:-1] + pad[:-2, 2:])
    )

    strength = 2.2
    nx = -gx * strength
    ny = -gy * strength
    nz = np.ones_like(lum)
    norm = np.sqrt(nx * nx + ny * ny + nz * nz) + 1e-6
    nx = (nx / norm) * 0.5 + 0.5
    ny = (ny / norm) * 0.5 + 0.5
    nz = (nz / norm) * 0.5 + 0.5

    normal_rgb = np.stack([nx, ny, nz], axis=-1)
    normal_rgb[alpha < 0.05] = np.array([0.5, 0.5, 1.0], dtype=np.float32)
    normal_img = Image.fromarray(np.clip(normal_rgb * 255.0, 0, 255).astype(np.uint8), mode="RGB")

    spec = np.clip((lum ** 1.3) * 1.45, 0.0, 1.0)
    spec[alpha < 0.05] = 0.0
    spec_rgb = np.stack([spec, spec, spec], axis=-1)
    spec_img = Image.fromarray(np.clip(spec_rgb * 255.0, 0, 255).astype(np.uint8), mode="RGB")

    return normal_img, spec_img


def write_sprite3d_material(unit_name: str) -> None:
    content = f"""[gd_resource type="StandardMaterial3D" load_steps=4 format=3]

[ext_resource type="Texture2D" path="res://tacplanshooter_hd/sprites/units_8dir/{unit_name}_8dir.png" id="1_diff"]
[ext_resource type="Texture2D" path="res://tacplanshooter_hd/sprites/units_8dir/{unit_name}_8dir_n.png" id="2_norm"]
[ext_resource type="Texture2D" path="res://tacplanshooter_hd/sprites/units_8dir/{unit_name}_8dir_s.png" id="3_spec"]

[resource]
transparency = 2
alpha_scissor_threshold = 0.5
albedo_texture = ExtResource("1_diff")
roughness_texture = ExtResource("3_spec")
normal_enabled = true
normal_texture = ExtResource("2_norm")
texture_filter = 0
billboard_mode = 2
"""
    (OUT_RES / f"{unit_name}_8dir_mat.tres").write_text(content, encoding="utf-8")


def main() -> int:
    OUT_SPRITES.mkdir(parents=True, exist_ok=True)
    OUT_RES.mkdir(parents=True, exist_ok=True)

    processed = 0
    for unit_name, raw_filename, mapping in UNITS:
        raw_path = RAW_DIR / raw_filename
        if not raw_path.exists():
            print(f"MISSING: {raw_path}", file=sys.stderr)
            continue
        raw_img = Image.open(raw_path)
        packed = pack_8dir_sheet(raw_img, mapping)
        normal_img, spec_img = build_normal_and_specular(packed)

        packed.save(OUT_SPRITES / f"{unit_name}_8dir.png")
        normal_img.save(OUT_SPRITES / f"{unit_name}_8dir_n.png")
        spec_img.save(OUT_SPRITES / f"{unit_name}_8dir_s.png")
        write_sprite3d_material(unit_name)
        print(f"PACKED: {unit_name}_8dir -> {packed.size[0]}x{packed.size[1]} (8 compass frames)")
        processed += 1

    if processed != len(UNITS):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
