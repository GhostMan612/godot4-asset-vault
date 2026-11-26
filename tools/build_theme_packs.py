#!/usr/bin/env python3
# ============================================================
# As Above, So Below. As Within, So Without.
# The Future Dictates the Past and the Past is Always Present.
# ============================================================
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
THEMES = ROOT / "themes"

PALETTES = {
    "tactical_compound": {"floor": (24, 34, 46), "floor_alt": (29, 40, 54), "wall": (14, 21, 31), "trim": (75, 94, 117), "grid": (0.06, 0.14, 0.20, 0.14)},
    "industrial_warehouse": {"floor": (48, 40, 32), "floor_alt": (58, 48, 38), "wall": (32, 28, 24), "trim": (200, 150, 40), "grid": (0.18, 0.11, 0.05, 0.16)},
    "moonbase_lab": {"floor": (32, 46, 58), "floor_alt": (38, 54, 68), "wall": (18, 30, 42), "trim": (60, 210, 230), "grid": (0.05, 0.20, 0.28, 0.17)},
    "bank_vault": {"floor": (42, 38, 30), "floor_alt": (52, 46, 36), "wall": (26, 24, 20), "trim": (190, 150, 60), "grid": (0.22, 0.17, 0.05, 0.15)},
    "ancestral_crypt": {"floor": (34, 44, 38), "floor_alt": (42, 52, 44), "wall": (22, 30, 26), "trim": (110, 140, 110), "grid": (0.05, 0.16, 0.10, 0.17)},
}


def normal_map(img: Image.Image) -> Image.Image:
    out = Image.new("RGBA", img.size, (128, 128, 255, 255))
    px = img.convert("RGBA").load()
    dst = out.load()
    for y in range(img.height):
        for x in range(img.width):
            l = sum(px[max(0, x - 1), y][:3]) / 3.0
            r = sum(px[min(img.width - 1, x + 1), y][:3]) / 3.0
            u = sum(px[x, max(0, y - 1)][:3]) / 3.0
            d = sum(px[x, min(img.height - 1, y + 1)][:3]) / 3.0
            nx = max(0, min(255, int(128 + (l - r) * 1.6)))
            ny = max(0, min(255, int(128 + (u - d) * 1.6)))
            dst[x, y] = (nx, ny, 255, 255)
    return out


def build_theme(theme_id: str, pal: dict) -> None:
    d = THEMES / theme_id
    d.mkdir(parents=True, exist_ok=True)
    floor = Image.new("RGBA", (256, 64), (0, 0, 0, 255))
    wall = Image.new("RGBA", (256, 64), (0, 0, 0, 255))
    props = Image.new("RGBA", (256, 64), (0, 0, 0, 0))
    fd, wd, pd = ImageDraw.Draw(floor), ImageDraw.Draw(wall), ImageDraw.Draw(props)
    for i in range(4):
        x = i * 64
        base = pal["floor"] if i % 2 == 0 else pal["floor_alt"]
        fd.rectangle((x, 0, x + 63, 63), fill=base)
        fd.rectangle((x + 2, 2, x + 61, 61), outline=pal["trim"], width=1)
        for k in range(0, 64, 16):
            fd.line((x + k, 4, x + k, 60), fill=tuple(int(c * 0.7) for c in base), width=1)
        wd.rectangle((x, 0, x + 63, 63), fill=pal["wall"])
        wd.rectangle((x + 2, 2, x + 61, 12), fill=pal["trim"])
        for k in range(20, 64, 12):
            wd.line((x + 4, k, x + 60, k), fill=tuple(int(c * 0.6) for c in pal["wall"]), width=1)
        pd.rectangle((x + 12, 12, x + 52, 52), fill=(*pal["wall"], 255), outline=pal["trim"], width=2)
        pd.ellipse((x + 24, 24, x + 40, 40), fill=pal["trim"])
    floor.save(d / "floor_atlas.png")
    normal_map(floor).save(d / "floor_atlas_n.png")
    wall.save(d / "wall_atlas.png")
    normal_map(wall).save(d / "wall_atlas_n.png")
    props.save(d / "props_atlas.png")
    meta = {
        "theme_id": theme_id,
        "floor_tiles": 4,
        "wall_face_variants": 4,
        "props": 4,
        "palette": {"floor": "#%02X%02X%02X" % pal["floor"], "wall": "#%02X%02X%02X" % pal["wall"], "trim": "#%02X%02X%02X" % pal["trim"]},
        "grid_color": list(pal["grid"]),
        "provenance": "ORIGINAL_PROCEDURAL",
    }
    (d / "theme_meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    for png in d.glob("*.png"):
        uid = "uid://" + hashlib.sha1((theme_id + png.name).encode()).hexdigest()[:12]
        imp = f'[remap]\n\nimporter="texture"\ntype="CompressedTexture2D"\nuid="{uid}"\npath="res://.godot/imported/{png.name}.ctex"\nmetadata={{\n"vram_texture": false\n}}\n\n[deps]\n\n'
        Path(str(png) + ".import").write_text(imp, encoding="utf-8")
    print(f"built {theme_id}")


if __name__ == "__main__":
    for theme_id, pal in PALETTES.items():
        build_theme(theme_id, pal)
