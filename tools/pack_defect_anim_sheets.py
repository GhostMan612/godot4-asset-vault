# As Above, So Below. As Within, So Without.
# The Future Dictates the Past and the Past is Always Present.

from pathlib import Path
import sys
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
PACK_DIR = ROOT / "sovereign_nodes_hd"
RAW_DIR = PACK_DIR / "raw"

CELL_SIZE = 256
COLS = 4
ROWS = 2

ROSTER = [
    ("archivist", "characters", "archivist_anim_raw.jpg", 8.0, 10.0),
    ("graver", "enemies", "graver_anim_raw.jpg", 7.0, 9.0),
    ("obituary_wailer", "enemies", "obituary_wailer_anim_raw.jpg", 8.0, 10.0),
    ("contract_breacher", "enemies", "contract_breacher_anim_raw.jpg", 6.0, 10.0),
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


def normalize_grid(sheet: Image.Image) -> Image.Image:
    w, h = sheet.size
    src_cw = w / COLS
    src_ch = h / ROWS
    canvas = Image.new("RGBA", (CELL_SIZE * COLS, CELL_SIZE * ROWS), (0, 0, 0, 0))
    margin = 10
    target_box = CELL_SIZE - margin * 2

    for row in range(ROWS):
        for col in range(COLS):
            box = (
                int(round(col * src_cw)),
                int(round(row * src_ch)),
                int(round((col + 1) * src_cw)),
                int(round((row + 1) * src_ch)),
            )
            cell = sheet.crop(box)
            bbox = cell.getbbox()
            if bbox is None:
                continue
            cropped = cell.crop(bbox)
            scale = min(target_box / cropped.width, target_box / cropped.height)
            new_w = max(1, int(round(cropped.width * scale)))
            new_h = max(1, int(round(cropped.height * scale)))
            resized = cropped.resize((new_w, new_h), Image.Resampling.NEAREST)
            dest_x = col * CELL_SIZE + (CELL_SIZE - new_w) // 2
            dest_y = row * CELL_SIZE + (CELL_SIZE - margin - new_h)
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

    strength = 2.4
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

    spec = np.clip((lum ** 1.35) * 1.4, 0.0, 1.0)
    spec[alpha < 0.05] = 0.0
    spec_rgb = np.stack([spec, spec, spec], axis=-1)
    spec_img = Image.fromarray(np.clip(spec_rgb * 255.0, 0, 255).astype(np.uint8), mode="RGB")

    return normal_img, spec_img


def write_canvas_texture(res_dir: Path, category: str, name: str) -> None:
    content = f"""[gd_resource type="CanvasTexture" load_steps=4 format=3]

[ext_resource type="Texture2D" path="res://sovereign_nodes_hd/sprites/{category}/{name}_anim.png" id="1_diff"]
[ext_resource type="Texture2D" path="res://sovereign_nodes_hd/sprites/{category}/{name}_anim_n.png" id="2_norm"]
[ext_resource type="Texture2D" path="res://sovereign_nodes_hd/sprites/{category}/{name}_anim_s.png" id="3_spec"]

[resource]
diffuse_texture = ExtResource("1_diff")
normal_texture = ExtResource("2_norm")
specular_texture = ExtResource("3_spec")
specular_shininess = 0.65
texture_filter = 1
"""
    (res_dir / f"{name}_canvas_tex.tres").write_text(content, encoding="utf-8")


def write_sprite_frames(res_dir: Path, category: str, name: str, walk_fps: float, attack_fps: float) -> None:
    sub_blocks = []
    for row in range(ROWS):
        for col in range(COLS):
            idx = row * COLS + col + 1
            sub_blocks.append(
                f"""[sub_resource type="AtlasTexture" id="AtlasTexture_{idx}"]
atlas = ExtResource("1_ctex")
region = Rect2({col * CELL_SIZE}, {row * CELL_SIZE}, {CELL_SIZE}, {CELL_SIZE})"""
            )

    walk_frames = ", ".join(
        f'{{\n"duration": 1.0,\n"texture": SubResource("AtlasTexture_{i}")\n}}'
        for i in range(1, 5)
    )
    attack_frames = ", ".join(
        f'{{\n"duration": 1.0,\n"texture": SubResource("AtlasTexture_{i}")\n}}'
        for i in range(5, 9)
    )

    content = f"""[gd_resource type="SpriteFrames" load_steps=10 format=3]

[ext_resource type="Texture2D" path="res://sovereign_nodes_hd/resources/{category}/{name}_canvas_tex.tres" id="1_ctex"]

{chr(10).join(sub_blocks)}

[resource]
animations = [{{
"frames": [{attack_frames}],
"loop": false,
"name": &"attack",
"speed": {attack_fps}
}}, {{
"frames": [{walk_frames}],
"loop": true,
"name": &"walk",
"speed": {walk_fps}
}}]
"""
    (res_dir / f"{name}_sprite_frames.tres").write_text(content, encoding="utf-8")


def main() -> int:
    processed = 0
    for name, category, raw_filename, walk_fps, attack_fps in ROSTER:
        raw_path = RAW_DIR / raw_filename
        if not raw_path.exists():
            print(f"MISSING: {raw_path}", file=sys.stderr)
            continue

        sprite_dir = PACK_DIR / "sprites" / category
        res_dir = PACK_DIR / "resources" / category
        sprite_dir.mkdir(parents=True, exist_ok=True)
        res_dir.mkdir(parents=True, exist_ok=True)

        raw_img = Image.open(raw_path)
        keyed = chroma_key_and_despill(raw_img)
        aligned = normalize_grid(keyed)
        normal_img, spec_img = build_normal_and_specular(aligned)

        aligned.save(sprite_dir / f"{name}_anim.png")
        normal_img.save(sprite_dir / f"{name}_anim_n.png")
        spec_img.save(sprite_dir / f"{name}_anim_s.png")
        write_canvas_texture(res_dir, category, name)
        write_sprite_frames(res_dir, category, name, walk_fps, attack_fps)
        print(f"PACKED: {category}/{name} -> {aligned.size[0]}x{aligned.size[1]} (4x2 @ {CELL_SIZE}px)")
        processed += 1

    if processed != len(ROSTER):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
