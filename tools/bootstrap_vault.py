# As Above, So Below. As Within, So Without.
# The Future Dictates the Past and the Past is Always Present.

from __future__ import annotations

import json
import math
import random
import struct
import wave
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
SEED = 612404

PALETTE = {
    "bg_dark": (13, 17, 23, 255),
    "slate_900": (22, 27, 34, 255),
    "slate_800": (33, 38, 45, 255),
    "slate_700": (48, 54, 61, 255),
    "slate_600": (72, 79, 88, 255),
    "slate_400": (139, 148, 158, 255),
    "slate_200": (201, 209, 217, 255),
    "cyan": (0, 229, 255, 255),
    "cyan_dim": (0, 140, 170, 255),
    "emerald": (46, 204, 113, 255),
    "amber": (255, 179, 0, 255),
    "crimson": (255, 59, 78, 255),
    "crimson_dark": (135, 28, 42, 255),
    "wood_dark": (62, 43, 34, 255),
    "wood_mid": (86, 61, 48, 255),
    "wood_light": (108, 78, 60, 255),
    "marble_a": (196, 203, 210, 255),
    "marble_b": (168, 176, 186, 255),
    "carpet": (36, 44, 58, 255),
    "sandbag": (152, 136, 104, 255),
    "glass": (110, 215, 240, 150),
    "white": (245, 248, 252, 255),
    "shadow": (0, 0, 0, 110),
}


def ensure_dirs() -> None:
    dirs = [
        "tacplanshooter/tilesets",
        "tacplanshooter/textures",
        "tacplanshooter/sprites",
        "tacplanshooter/resources",
        "tacplanshooter/ui/icons",
        "tacplanshooter/ui/themes",
        "tacplanshooter/shaders",
        "tacplanshooter/audio/sfx",
    ]
    for d in dirs:
        (ROOT / d).mkdir(parents=True, exist_ok=True)


def add_grain(img: Image.Image, rng: random.Random, strength: int = 8) -> Image.Image:
    px = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            d = rng.randint(-strength, strength)
            px[x, y] = (
                max(0, min(255, r + d)),
                max(0, min(255, g + d)),
                max(0, min(255, b + d)),
                a,
            )
    return img


def make_seamless_concrete(size: int = 256) -> Image.Image:
    rng = random.Random(SEED + 1)
    img = Image.new("RGBA", (size, size), (68, 74, 82, 255))
    draw = ImageDraw.Draw(img)
    for _ in range(280):
        x = rng.randint(0, size - 1)
        y = rng.randint(0, size - 1)
        rad = rng.randint(2, 14)
        tone = rng.randint(58, 82)
        col = (tone, tone + 4, tone + 9, 45)
        for ox in (-size, 0, size):
            for oy in (-size, 0, size):
                draw.ellipse((x + ox - rad, y + oy - rad, x + ox + rad, y + oy + rad), fill=col)
    for s in (0, size // 2):
        draw.line((s, 0, s, size), fill=(48, 54, 61, 120), width=2)
        draw.line((0, s, size, s), fill=(48, 54, 61, 120), width=2)
    return add_grain(img, rng, 6)


def make_seamless_hardwood(size: int = 256) -> Image.Image:
    rng = random.Random(SEED + 2)
    img = Image.new("RGBA", (size, size), PALETTE["wood_dark"])
    draw = ImageDraw.Draw(img)
    plank_h = 32
    for row in range(size // plank_h):
        y0 = row * plank_h
        offset = (row % 2) * 64
        for seg in range(-1, 3):
            x0 = seg * 128 + offset
            shade = rng.randint(-8, 10)
            col = (
                max(0, min(255, PALETTE["wood_mid"][0] + shade)),
                max(0, min(255, PALETTE["wood_mid"][1] + shade)),
                max(0, min(255, PALETTE["wood_mid"][2] + shade)),
                255,
            )
            draw.rectangle((x0, y0, x0 + 127, y0 + plank_h - 1), fill=col, outline=(40, 27, 20, 255), width=2)
            for g in range(4, plank_h - 4, 6):
                draw.line((x0 + 3, y0 + g, x0 + 124, y0 + g), fill=(52, 36, 28, 90), width=1)
    return add_grain(img, rng, 4)


def make_seamless_grate(size: int = 256) -> Image.Image:
    rng = random.Random(SEED + 3)
    img = Image.new("RGBA", (size, size), (24, 29, 36, 255))
    draw = ImageDraw.Draw(img)
    step = 16
    for y in range(0, size, step):
        for x in range(0, size, step):
            draw.rectangle((x + 2, y + 2, x + step - 3, y + step - 3), fill=(15, 19, 24, 255), outline=(62, 72, 84, 255), width=2)
    for s in (0, size // 2):
        draw.rectangle((s, 0, s + 4, size), fill=(76, 86, 98, 255))
        draw.rectangle((0, s, size, s + 4), fill=(76, 86, 98, 255))
    return add_grain(img, rng, 4)


def make_tactical_grid_overlay(size: int = 256) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    for i in range(0, size, 32):
        alpha = 70 if i % 64 == 0 else 28
        draw.line((i, 0, i, size), fill=(0, 229, 255, alpha), width=1)
        draw.line((0, i, size, i), fill=(0, 229, 255, alpha), width=1)
    for y in range(0, size, 64):
        for x in range(0, size, 64):
            draw.line((x - 4, y, x + 4, y), fill=(0, 229, 255, 130), width=1)
            draw.line((x, y - 4, x, y + 4), fill=(0, 229, 255, 130), width=1)
    return img


def make_fog_noise(size: int = 256) -> Image.Image:
    rng = random.Random(SEED + 4)
    grid = 16
    vals = [[rng.random() for _ in range(grid)] for _ in range(grid)]
    img = Image.new("RGBA", (size, size))
    px = img.load()
    for y in range(size):
        gy = (y / size) * grid
        y0 = int(gy) % grid
        y1 = (y0 + 1) % grid
        ty = gy - int(gy)
        sy = ty * ty * (3 - 2 * ty)
        for x in range(size):
            gx = (x / size) * grid
            x0 = int(gx) % grid
            x1 = (x0 + 1) % grid
            tx = gx - int(gx)
            sx = tx * tx * (3 - 2 * tx)
            a = vals[y0][x0] * (1 - sx) + vals[y0][x1] * sx
            b = vals[y1][x0] * (1 - sx) + vals[y1][x1] * sx
            v = a * (1 - sy) + b * sy
            v2 = vals[(y0 * 2) % grid][(x0 * 2) % grid]
            c = int(max(0, min(255, (v * 0.72 + v2 * 0.28) * 255)))
            px[x, y] = (c, c, c, 255)
    return img.filter(ImageFilter.GaussianBlur(radius=1.2))


def draw_floor_tile(idx: int, tile_size: int = 64) -> Image.Image:
    s = tile_size * 2
    rng = random.Random(SEED + 100 + idx)
    img = Image.new("RGBA", (s, s), (68, 74, 82, 255))
    d = ImageDraw.Draw(img)

    if idx in (0, 1, 2, 3):
        base = (66 + idx * 4, 72 + idx * 4, 80 + idx * 4, 255)
        d.rectangle((0, 0, s - 1, s - 1), fill=base, outline=(48, 54, 61, 255), width=2)
        if idx == 1:
            d.line((18, 22, 62, 50, 96, 44), fill=(42, 46, 52, 180), width=3)
        elif idx == 2:
            d.rectangle((12, 12, s - 12, s - 12), outline=(88, 96, 106, 140), width=2)
        elif idx == 3:
            for k in range(16, s, 32):
                d.ellipse((k - 3, 12, k + 3, 18), fill=(40, 44, 50, 200))
                d.ellipse((k - 3, s - 18, k + 3, s - 12), fill=(40, 44, 50, 200))
    elif idx in (4, 5, 6, 7):
        d.rectangle((0, 0, s - 1, s - 1), fill=PALETTE["wood_dark"])
        for row in range(4):
            y0 = row * (s // 4)
            shade = (idx - 5) * 6 + (row % 2) * 8
            col = (84 + shade, 60 + shade, 46 + shade, 255)
            d.rectangle((0, y0, s - 1, y0 + s // 4 - 1), fill=col, outline=(42, 28, 20, 255), width=2)
    elif idx in (8, 9, 10, 11):
        c1, c2 = PALETTE["marble_a"], PALETTE["marble_b"]
        half = s // 2
        if idx in (8, 9):
            for ry in range(2):
                for rx in range(2):
                    c = c1 if (rx + ry + idx) % 2 == 0 else c2
                    d.rectangle((rx * half, ry * half, (rx + 1) * half - 1, (ry + 1) * half - 1), fill=c, outline=(130, 138, 148, 255), width=2)
        else:
            d.rectangle((0, 0, s - 1, s - 1), fill=PALETTE["carpet"], outline=(26, 32, 44, 255), width=2)
            for y in range(8, s, 16):
                d.line((6, y, s - 6, y), fill=(46, 56, 74, 160), width=2)
            if idx == 11:
                d.rectangle((10, 10, s - 10, s - 10), outline=PALETTE["amber"], width=3)
    elif idx in (12, 13, 14, 15):
        d.rectangle((0, 0, s - 1, s - 1), fill=(26, 32, 40, 255), outline=(64, 74, 86, 255), width=3)
        for y in range(12, s - 8, 20):
            for x in range(12, s - 8, 20):
                d.rectangle((x, y, x + 12, y + 12), fill=(14, 18, 24, 255), outline=(56, 66, 78, 255), width=2)
        if idx == 13:
            d.rectangle((0, s - 22, s - 1, s - 1), fill=PALETTE["amber"])
            for x in range(-s, s * 2, 24):
                d.polygon([(x, s), (x + 12, s), (x + 26, s - 22), (x + 14, s - 22)], fill=(22, 24, 28, 255))
        elif idx == 14:
            d.rectangle((0, 0, s - 1, s - 1), fill=(52, 58, 66, 255), outline=PALETTE["cyan_dim"], width=4)
            d.polygon([(s // 2, 24), (s - 28, s - 32), (28, s - 32)], fill=PALETTE["cyan"])
        elif idx == 15:
            d.rectangle((0, 0, s - 1, s - 1), fill=(52, 58, 66, 255), outline=PALETTE["amber"], width=4)
            d.polygon([(s // 2, s - 24), (s - 28, 32), (28, 32)], fill=PALETTE["amber"])
    elif idx in (16, 17, 18, 19):
        d.rectangle((0, 0, s - 1, s - 1), fill=(56, 62, 70, 255), outline=(34, 38, 44, 255), width=3)
        steps = 6
        for st in range(steps):
            y0 = int(st * (s / steps))
            tone = 44 + st * 10 if idx % 2 == 0 else 104 - st * 10
            d.rectangle((8, y0, s - 8, y0 + s // steps - 2), fill=(tone, tone + 4, tone + 8, 255), outline=(28, 32, 38, 255), width=2)
        arrow_col = PALETTE["cyan"] if idx in (16, 18) else PALETTE["amber"]
        if idx in (16, 18):
            d.polygon([(s // 2, 18), (s // 2 + 20, 44), (s // 2 - 20, 44)], fill=arrow_col)
        else:
            d.polygon([(s // 2, s - 18), (s // 2 + 20, s - 44), (s // 2 - 20, s - 44)], fill=arrow_col)
    elif idx in (20, 21, 22, 23):
        d.rectangle((0, 0, s - 1, s - 1), fill=(46, 52, 60, 255), outline=(80, 90, 102, 255), width=3)
        if idx == 20:
            d.rectangle((14, 14, s - 14, s - 14), outline=PALETTE["emerald"], width=5)
            d.line((28, s // 2, s - 28, s // 2), fill=PALETTE["emerald"], width=4)
            d.line((s // 2, 28, s // 2, s - 28), fill=PALETTE["emerald"], width=4)
        elif idx == 21:
            d.rectangle((14, 14, s - 14, s - 14), outline=PALETTE["crimson"], width=5)
            d.line((28, 28, s - 28, s - 28), fill=PALETTE["crimson"], width=5)
            d.line((s - 28, 28, 28, s - 28), fill=PALETTE["crimson"], width=5)
        elif idx == 22:
            d.ellipse((24, 24, s - 24, s - 24), fill=(26, 26, 30, 210))
            for _ in range(14):
                rx, ry = rng.randint(18, s - 18), rng.randint(18, s - 18)
                d.rectangle((rx - 4, ry - 4, rx + 4, ry + 4), fill=(95, 98, 104, 255))
        else:
            d.rectangle((10, 10, s - 10, s - 10), fill=(76, 84, 94, 255), outline=(120, 130, 142, 255), width=3)
            d.line((s // 2, 10, s // 2, s - 10), fill=(36, 42, 50, 255), width=4)
    else:
        tone = 34 + (idx - 24) * 5
        d.rectangle((0, 0, s - 1, s - 1), fill=(tone, tone + 6, tone + 12, 255), outline=(0, 229, 255, 90), width=2)
        d.line((0, s // 2, s, s // 2), fill=(0, 229, 255, 50), width=1)
        d.line((s // 2, 0, s // 2, s), fill=(0, 229, 255, 50), width=1)

    img = add_grain(img, rng, 4)
    return img.resize((tile_size, tile_size), Image.Resampling.LANCZOS)


def draw_wall_cover_tile(idx: int, tile_size: int = 64) -> Image.Image:
    s = tile_size * 2
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    w_fill = (42, 48, 56, 255)
    w_top = (76, 86, 98, 255)
    w_edge = (18, 22, 28, 255)

    def wall_rect(x0: int, y0: int, x1: int, y1: int) -> None:
        d.rectangle((x0 + 4, y0 + 4, x1 + 4, y1 + 4), fill=PALETTE["shadow"])
        d.rectangle((x0, y0, x1, y1), fill=w_fill, outline=w_edge, width=3)
        d.rectangle((x0 + 6, y0 + 6, x1 - 6, y1 - 6), fill=w_top)

    if idx == 0:
        wall_rect(0, 40, s, 88)
    elif idx == 1:
        wall_rect(40, 0, 88, s)
    elif idx == 2:
        wall_rect(40, 40, s, 88)
        wall_rect(40, 40, 88, s)
    elif idx == 3:
        wall_rect(0, 40, 88, 88)
        wall_rect(40, 40, 88, s)
    elif idx == 4:
        wall_rect(40, 0, 88, 88)
        wall_rect(40, 40, s, 88)
    elif idx == 5:
        wall_rect(0, 40, 88, 88)
        wall_rect(40, 0, 88, 88)
    elif idx == 6:
        wall_rect(0, 40, s, 88)
        wall_rect(40, 40, 88, s)
    elif idx == 7:
        wall_rect(0, 40, s, 88)
        wall_rect(40, 0, 88, s)
    elif idx == 8:
        wall_rect(28, 28, s - 28, s - 28)
    elif idx == 9:
        d.rectangle((0, 52, s, 76), fill=PALETTE["glass"], outline=PALETTE["cyan"], width=3)
        d.line((16, 56, 36, 72), fill=PALETTE["white"], width=3)
        d.line((76, 56, 96, 72), fill=PALETTE["white"], width=3)
    elif idx == 10:
        d.rectangle((52, 0, 76, s), fill=PALETTE["glass"], outline=PALETTE["cyan"], width=3)
        d.line((56, 20, 72, 40), fill=PALETTE["white"], width=3)
        d.line((56, 80, 72, 100), fill=PALETTE["white"], width=3)
    elif idx == 11:
        wall_rect(0, 40, 26, 88)
        wall_rect(s - 26, 40, s, 88)
        d.rectangle((24, 54, s - 24, 74), fill=PALETTE["wood_mid"], outline=(35, 22, 15, 255), width=3)
        d.ellipse((s - 38, 60, s - 30, 68), fill=PALETTE["amber"])
    elif idx == 12:
        wall_rect(0, 40, 26, 88)
        wall_rect(s - 26, 40, s, 88)
        d.rectangle((22, 64, 42, s - 6), fill=PALETTE["wood_mid"], outline=(35, 22, 15, 255), width=3)
        d.arc((24, 24, s - 24, s - 12), start=0, end=90, fill=(0, 229, 255, 130), width=2)
    elif idx == 13:
        wall_rect(0, 40, 24, 88)
        wall_rect(s - 24, 40, s, 88)
        d.rectangle((22, 48, s - 22, 80), fill=(72, 78, 88, 255), outline=PALETTE["amber"], width=4)
        d.line((44, 54, 84, 74), fill=PALETTE["amber"], width=4)
        d.line((84, 54, 44, 74), fill=PALETTE["amber"], width=4)
    elif idx == 14:
        wall_rect(0, 40, 24, 88)
        wall_rect(s - 24, 40, s, 88)
        for bx in range(30, s - 28, 14):
            d.line((bx, 48, bx, 80), fill=(150, 160, 172, 255), width=4)
        d.line((24, 64, s - 24, 64), fill=(110, 120, 132, 255), width=5)
    elif idx == 15:
        wall_rect(0, 40, 28, 88)
        wall_rect(s - 28, 40, s, 88)
        d.rectangle((28, 52, s - 28, 76), fill=(110, 215, 240, 120), outline=PALETTE["slate_200"], width=3)
    elif idx == 16:
        d.rectangle((14, 34, s - 10, s - 30), fill=PALETTE["shadow"])
        d.rectangle((10, 30, s - 14, s - 34), fill=(104, 112, 122, 255), outline=w_edge, width=3)
        d.rectangle((18, 38, s - 22, s - 42), fill=(128, 136, 146, 255))
        d.line((18, 64, s - 22, 64), fill=PALETTE["amber"], width=4)
    elif idx == 17:
        for bx in (20, 50, 80):
            d.rounded_rectangle((bx, 38, bx + 34, 88), radius=10, fill=PALETTE["sandbag"], outline=(74, 64, 48, 255), width=3)
    elif idx == 18:
        d.rectangle((14, 24, s - 10, s - 20), fill=PALETTE["shadow"])
        d.rectangle((10, 20, s - 14, s - 24), fill=PALETTE["wood_mid"], outline=(36, 24, 18, 255), width=3)
        d.rectangle((22, 32, 74, 66), fill=(32, 38, 46, 255), outline=PALETTE["cyan_dim"], width=2)
        d.rectangle((84, 36, 102, 54), fill=(200, 208, 216, 255))
    elif idx == 19:
        d.rectangle((20, 16, s - 16, s - 12), fill=PALETTE["shadow"])
        d.rectangle((16, 12, s - 20, s - 16), fill=(26, 32, 42, 255), outline=(72, 82, 96, 255), width=3)
        for ry in range(24, s - 26, 18):
            d.rectangle((24, ry, s - 28, ry + 10), fill=(40, 48, 60, 255))
            d.ellipse((s - 40, ry + 2, s - 34, ry + 8), fill=PALETTE["emerald"] if ry % 36 == 0 else PALETTE["cyan"])
    elif idx == 20:
        d.rectangle((22, 22, s - 18, s - 18), fill=PALETTE["shadow"])
        d.rectangle((18, 18, s - 22, s - 22), fill=(72, 84, 68, 255), outline=(28, 34, 26, 255), width=3)
        d.line((24, 24, s - 28, s - 28), fill=(52, 62, 48, 255), width=4)
        d.line((s - 28, 24, 24, s - 28), fill=(52, 62, 48, 255), width=4)
        d.rectangle((48, 48, s - 48, s - 48), fill=PALETTE["amber"])
    elif idx == 21:
        d.ellipse((24, 24, s - 20, s - 20), fill=PALETTE["shadow"])
        d.ellipse((20, 20, s - 24, s - 24), fill=(46, 86, 56, 255), outline=(24, 48, 30, 255), width=3)
        d.ellipse((36, 36, s - 40, s - 40), fill=(68, 126, 78, 255))
    elif idx == 22:
        d.rounded_rectangle((18, 28, s - 18, s - 28), radius=14, fill=(58, 64, 76, 255), outline=(26, 30, 38, 255), width=3)
        d.rounded_rectangle((24, 34, s - 24, 54), radius=8, fill=(76, 84, 98, 255))
    else:
        d.rectangle((26, 26, s - 26, s - 26), fill=(62, 70, 82, 255), outline=PALETTE["cyan_dim"], width=3)
        d.ellipse((46, 46, s - 46, s - 46), fill=PALETTE["amber"] if idx % 2 == 0 else PALETTE["cyan"])

    return img.resize((tile_size, tile_size), Image.Resampling.LANCZOS)


def draw_character_sprite(is_hostile: bool, role: int, state: int, size: int = 64) -> Image.Image:
    s = size * 2
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    cx, cy = s // 2, s // 2
    if is_hostile:
        vest_cols = [(140, 38, 48, 255), (175, 42, 56, 255), (105, 34, 44, 255), (190, 140, 42, 255)]
        helm_cols = [(52, 24, 28, 255), (72, 28, 34, 255), (42, 42, 50, 255), (210, 178, 145, 255)]
        accent = PALETTE["crimson"] if role < 3 else PALETTE["amber"]
    else:
        vest_cols = [(36, 56, 74, 255), (48, 66, 54, 255), (42, 48, 68, 255), (34, 52, 64, 255)]
        helm_cols = [(24, 34, 44, 255), (30, 42, 36, 255), (28, 32, 46, 255), (20, 30, 40, 255)]
        accent = [PALETTE["cyan"], PALETTE["amber"], PALETTE["emerald"], PALETTE["white"]][role]

    if is_hostile and state == 3:
        d.ellipse((24, 36, s - 24, s - 36), fill=(110, 20, 30, 170))
        d.rounded_rectangle((30, 48, s - 30, 80), radius=12, fill=vest_cols[role], outline=(20, 20, 24, 255), width=3)
        d.ellipse((s - 46, 48, s - 16, 78), fill=helm_cols[role], outline=(20, 20, 24, 255), width=3)
        return img.resize((size, size), Image.Resampling.LANCZOS)

    shift_x = 4 if state == 2 else 0
    crouch = 4 if (not is_hostile and state == 3) else 0

    d.ellipse((cx - 34 + shift_x, cy - 30, cx + 38 + shift_x, cy + 36), fill=PALETTE["shadow"])

    if not is_hostile and role == 3:
        d.rounded_rectangle((cx + 22 + shift_x, cy - 34, cx + 36 + shift_x, cy + 34), radius=6, fill=(44, 52, 62, 255), outline=PALETTE["cyan"], width=3)
        d.rectangle((cx + 25 + shift_x, cy - 12, cx + 33 + shift_x, cy + 12), fill=PALETTE["glass"])

    w_len = [42, 36, 30, 24][role]
    w_thick = [8, 10, 7, 7][role]
    if state in (1, 2):
        w_len += 6
    d.rounded_rectangle((cx + 6 + shift_x, cy + 2, cx + 6 + w_len + shift_x, cy + 2 + w_thick), radius=2, fill=(32, 36, 42, 255), outline=(14, 16, 20, 255), width=2)
    if state == 1:
        d.line((cx + 8 + w_len + shift_x, cy + 5, s - 6, cy + 5), fill=(accent[0], accent[1], accent[2], 140), width=2)

    shoulder_rx = 24 - crouch // 2
    shoulder_ry = 30 - crouch
    d.rounded_rectangle(
        (cx - shoulder_rx + shift_x, cy - shoulder_ry, cx + shoulder_rx + shift_x, cy + shoulder_ry),
        radius=16,
        fill=vest_cols[role],
        outline=(16, 20, 26, 255),
        width=3,
    )
    d.line((cx - 8 + shift_x, cy - shoulder_ry + 8, cx - 8 + shift_x, cy + shoulder_ry - 8), fill=accent, width=4)

    head_r = 17 - crouch // 3
    d.ellipse((cx - head_r + shift_x + 3, cy - head_r, cx + head_r + shift_x + 3, cy + head_r), fill=helm_cols[role], outline=(16, 20, 26, 255), width=3)
    d.arc((cx - head_r + shift_x + 5, cy - head_r + 3, cx + head_r + shift_x + 1, cy + head_r - 3), start=300, end=60, fill=accent, width=4)

    return img.resize((size, size), Image.Resampling.LANCZOS)


def draw_prop_fx(idx: int, size: int = 64) -> Image.Image:
    s = size * 2
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, cy = s // 2, s // 2

    if idx == 0:
        d.rounded_rectangle((46, 30, 82, 98), radius=10, fill=(68, 76, 86, 255), outline=(18, 22, 28, 255), width=3)
        d.rectangle((46, 54, 82, 72), fill=PALETTE["amber"])
        d.ellipse((54, 18, 74, 34), outline=PALETTE["slate_200"], width=4)
    elif idx == 1:
        d.rounded_rectangle((46, 30, 82, 98), radius=10, fill=(58, 78, 66, 255), outline=(18, 22, 28, 255), width=3)
        d.rectangle((46, 54, 82, 72), fill=PALETTE["emerald"])
        d.rectangle((56, 20, 72, 32), fill=PALETTE["slate_400"])
    elif idx == 2:
        d.rounded_rectangle((30, 38, 98, 90), radius=8, fill=(56, 62, 70, 255), outline=(18, 22, 28, 255), width=3)
        d.rectangle((42, 48, 86, 78), fill=(32, 36, 42, 255))
        d.ellipse((58, 57, 70, 69), fill=PALETTE["crimson"])
    elif idx == 3:
        d.rounded_rectangle((28, 34, 100, 94), radius=10, fill=PALETTE["white"], outline=(40, 48, 56, 255), width=3)
        d.rectangle((56, 44, 72, 84), fill=PALETTE["crimson"])
        d.rectangle((44, 56, 84, 72), fill=PALETTE["crimson"])
    elif idx == 4:
        d.rounded_rectangle((24, 36, 104, 96), radius=8, fill=(38, 44, 54, 255), outline=PALETTE["cyan"], width=3)
        d.rectangle((50, 24, 78, 38), outline=PALETTE["cyan"], width=4)
        d.rectangle((56, 60, 72, 72), fill=PALETTE["amber"])
    elif idx == 5:
        d.rounded_rectangle((26, 40, 102, 88), radius=8, fill=PALETTE["cyan"], outline=(18, 22, 28, 255), width=3)
        d.rectangle((26, 52, 102, 64), fill=(22, 28, 36, 255))
        d.rectangle((36, 70, 62, 80), fill=PALETTE["white"])
    elif idx == 6:
        d.ellipse((18, 18, s - 18, s - 18), outline=PALETTE["cyan"], width=5)
        d.ellipse((44, 44, s - 44, s - 44), fill=PALETTE["cyan"])
    elif idx == 7:
        d.ellipse((20, 20, s - 20, s - 20), outline=PALETTE["crimson"], width=5)
        for p in ((cx, 8, cx, 32), (cx, s - 32, cx, s - 8), (8, cy, 32, cy), (s - 32, cy, s - 8, cy)):
            d.line(p, fill=PALETTE["crimson"], width=5)
    elif idx in (8, 9, 10):
        scale = 1.0 - (idx - 8) * 0.22
        pts = []
        for k in range(12):
            ang = k * math.pi / 6
            rad = (48 if k % 2 == 0 else 20) * scale
            pts.append((cx + math.cos(ang) * rad, cy + math.sin(ang) * rad))
        d.polygon(pts, fill=(255, 210, 70, 230))
        d.ellipse((cx - int(18 * scale), cy - int(18 * scale), cx + int(18 * scale), cy + int(18 * scale)), fill=(255, 255, 230, 255))
    elif idx in (11, 12, 13):
        alpha = [180, 130, 80][idx - 11]
        rad = [30, 40, 48][idx - 11]
        for ox, oy, r in ((-14, -10, rad), (16, -6, rad - 4), (0, 14, rad - 2)):
            d.ellipse((cx + ox - r, cy + oy - r, cx + ox + r, cy + oy + r), fill=(190, 200, 210, alpha))
    elif idx == 14:
        for ang_deg in range(0, 360, 45):
            a = math.radians(ang_deg)
            d.line((cx + math.cos(a) * 10, cy + math.sin(a) * 10, cx + math.cos(a) * 46, cy + math.sin(a) * 46), fill=PALETTE["amber"], width=4)
    else:
        d.ellipse((24, 24, s - 24, s - 24), fill=(30, 24, 24, 180))
        d.ellipse((38, 38, s - 38, s - 38), fill=(18, 16, 18, 210))

    return img.resize((size, size), Image.Resampling.LANCZOS)


SVG_ICONS: dict[str, tuple[str, str]] = {
    "icon_draw_mode": ("#00E5FF", '<path d="M12 52 L20 36 L44 12 L52 20 L28 44 Z" fill="none" stroke="{c}" stroke-width="4" stroke-linejoin="round"/><path d="M12 52 Q24 54 34 46 T54 44" fill="none" stroke="{c}" stroke-width="3" stroke-dasharray="4 3"/>'),
    "icon_tap_mode": ("#00E5FF", '<circle cx="32" cy="24" r="14" fill="none" stroke="{c}" stroke-width="3" stroke-dasharray="4 3"/><circle cx="32" cy="24" r="5" fill="{c}"/><path d="M32 28 L32 54 M24 44 L32 54 L40 44" fill="none" stroke="{c}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>'),
    "icon_breach": ("#FFB300", '<polygon points="32,8 38,24 56,22 42,34 50,52 32,42 14,52 22,34 8,22 26,24" fill="none" stroke="{c}" stroke-width="4" stroke-linejoin="round"/><circle cx="32" cy="32" r="6" fill="{c}"/>'),
    "icon_flashbang": ("#FFB300", '<rect x="22" y="18" width="20" height="36" rx="4" fill="none" stroke="{c}" stroke-width="4"/><line x1="22" y1="30" x2="42" y2="30" stroke="{c}" stroke-width="4"/><line x1="22" y1="42" x2="42" y2="42" stroke="{c}" stroke-width="4"/><path d="M26 18 V12 H38" fill="none" stroke="{c}" stroke-width="4"/>'),
    "icon_smoke": ("#2ECC71", '<circle cx="24" cy="38" r="10" fill="none" stroke="{c}" stroke-width="4"/><circle cx="38" cy="36" r="12" fill="none" stroke="{c}" stroke-width="4"/><circle cx="30" cy="24" r="10" fill="none" stroke="{c}" stroke-width="4"/>'),
    "icon_stairs_up": ("#00E5FF", '<path d="M12 50 H24 V38 H36 V26 H52" fill="none" stroke="{c}" stroke-width="4" stroke-linejoin="round"/><path d="M14 26 L30 12 M20 12 H30 V22" fill="none" stroke="{c}" stroke-width="4" stroke-linecap="round"/>'),
    "icon_stairs_down": ("#FFB300", '<path d="M12 20 H24 V32 H36 V44 H52" fill="none" stroke="{c}" stroke-width="4" stroke-linejoin="round"/><path d="M36 12 L52 26 M42 26 H52 V16" fill="none" stroke="{c}" stroke-width="4" stroke-linecap="round"/>'),
    "icon_briefing": ("#00E5FF", '<rect x="14" y="10" width="36" height="44" rx="4" fill="none" stroke="{c}" stroke-width="4"/><line x1="22" y1="22" x2="42" y2="22" stroke="{c}" stroke-width="3"/><line x1="22" y1="32" x2="42" y2="32" stroke="{c}" stroke-width="3"/><line x1="22" y1="42" x2="34" y2="42" stroke="{c}" stroke-width="3"/>'),
    "icon_intel": ("#00E5FF", '<path d="M10 32 Q32 12 54 32 Q32 52 10 32 Z" fill="none" stroke="{c}" stroke-width="4"/><circle cx="32" cy="32" r="8" fill="{c}"/>'),
    "icon_roster": ("#00E5FF", '<circle cx="24" cy="22" r="7" fill="none" stroke="{c}" stroke-width="4"/><path d="M12 48 C12 36 36 36 36 48" fill="none" stroke="{c}" stroke-width="4"/><circle cx="44" cy="24" r="5" fill="none" stroke="{c}" stroke-width="3"/><path d="M38 48 C38 39 54 39 54 48" fill="none" stroke="{c}" stroke-width="3"/>'),
    "icon_kit": ("#FFB300", '<rect x="12" y="20" width="40" height="32" rx="4" fill="none" stroke="{c}" stroke-width="4"/><path d="M24 20 V12 H40 V20" fill="none" stroke="{c}" stroke-width="4"/><line x1="12" y1="34" x2="52" y2="34" stroke="{c}" stroke-width="3"/>'),
    "icon_team": ("#2ECC71", '<polygon points="32,10 52,22 52,44 32,54 12,44 12,22" fill="none" stroke="{c}" stroke-width="4"/><circle cx="32" cy="32" r="8" fill="{c}"/>'),
    "icon_play": ("#2ECC71", '<polygon points="20,14 50,32 20,50" fill="{c}"/>'),
    "icon_pause": ("#FFB300", '<rect x="18" y="14" width="10" height="36" rx="2" fill="{c}"/><rect x="36" y="14" width="10" height="36" rx="2" fill="{c}"/>'),
    "icon_rewind": ("#00E5FF", '<polygon points="32,16 12,32 32,48" fill="{c}"/><polygon points="52,16 32,32 52,48" fill="{c}"/>'),
    "icon_shield": ("#00E5FF", '<path d="M32 8 L50 16 V32 C50 44 42 52 32 56 C22 52 14 44 14 32 V16 Z" fill="none" stroke="{c}" stroke-width="4" stroke-linejoin="round"/><line x1="32" y1="16" x2="32" y2="48" stroke="{c}" stroke-width="3"/>'),
    "icon_target": ("#FF3B4E", '<circle cx="32" cy="32" r="18" fill="none" stroke="{c}" stroke-width="4"/><circle cx="32" cy="32" r="6" fill="{c}"/><line x1="32" y1="6" x2="32" y2="18" stroke="{c}" stroke-width="4"/><line x1="32" y1="46" x2="32" y2="58" stroke="{c}" stroke-width="4"/><line x1="6" y1="32" x2="18" y2="32" stroke="{c}" stroke-width="4"/><line x1="46" y1="32" x2="58" y2="32" stroke="{c}" stroke-width="4"/>'),
    "icon_waypoint": ("#00E5FF", '<path d="M32 56 C32 56 50 38 50 24 A18 18 0 1 0 14 24 C14 38 32 56 32 56 Z" fill="none" stroke="{c}" stroke-width="4"/><circle cx="32" cy="24" r="6" fill="{c}"/>'),
    "icon_lock": ("#FF3B4E", '<rect x="16" y="28" width="32" height="24" rx="4" fill="none" stroke="{c}" stroke-width="4"/><path d="M22 28 V20 A10 10 0 0 1 42 20 V28" fill="none" stroke="{c}" stroke-width="4"/><circle cx="32" cy="40" r="4" fill="{c}"/>'),
    "icon_lan_coop": ("#2ECC71", '<rect x="10" y="12" width="18" height="14" rx="2" fill="none" stroke="{c}" stroke-width="3"/><rect x="36" y="38" width="18" height="14" rx="2" fill="none" stroke="{c}" stroke-width="3"/><path d="M28 19 H45 V38 M19 26 V45 H36" fill="none" stroke="{c}" stroke-width="3"/>'),
}


def hex_to_rgba(h: str) -> tuple[int, int, int, int]:
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255)


def render_icon_png(name: str, color_hex: str, size: int = 64) -> Image.Image:
    s = size * 2
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    col = hex_to_rgba(color_hex)
    d.rounded_rectangle((6, 6, s - 6, s - 6), radius=18, fill=(20, 26, 34, 225), outline=col, width=4)
    cx, cy = s // 2, s // 2

    if name == "icon_draw_mode":
        d.polygon([(30, 96), (42, 68), (84, 26), (100, 42), (58, 84)], outline=col, width=6)
        d.line((30, 96, 98, 96), fill=col, width=5)
    elif name == "icon_tap_mode":
        d.ellipse((38, 22, 90, 74), outline=col, width=5)
        d.ellipse((56, 40, 72, 56), fill=col)
        d.line((cx, 56, cx, 104), fill=col, width=6)
    elif name == "icon_breach":
        pts = [(cx + math.cos(k * math.pi / 5 - math.pi / 2) * (40 if k % 2 == 0 else 18), cy + math.sin(k * math.pi / 5 - math.pi / 2) * (40 if k % 2 == 0 else 18)) for k in range(10)]
        d.polygon(pts, outline=col, width=6)
        d.ellipse((cx - 10, cy - 10, cx + 10, cy + 10), fill=col)
    elif name == "icon_flashbang":
        d.rounded_rectangle((46, 36, 82, 102), radius=8, outline=col, width=6)
        d.line((46, 58, 82, 58), fill=col, width=6)
        d.line((46, 78, 82, 78), fill=col, width=6)
        d.line((54, 24, 74, 24), fill=col, width=6)
    elif name == "icon_smoke":
        for ox, oy, r in ((-14, 10, 18), (14, 8, 20), (0, -12, 18)):
            d.ellipse((cx + ox - r, cy + oy - r, cx + ox + r, cy + oy + r), outline=col, width=6)
    elif name == "icon_stairs_up":
        d.line((26, 98, 50, 98, 50, 74, 74, 74, 74, 50, 102, 50), fill=col, width=7)
        d.polygon([(52, 26), (34, 44), (58, 44)], fill=col)
    elif name == "icon_stairs_down":
        d.line((26, 38, 50, 38, 50, 62, 74, 62, 74, 86, 102, 86), fill=col, width=7)
        d.polygon([(92, 58), (74, 40), (98, 40)], fill=col)
    elif name == "icon_briefing":
        d.rounded_rectangle((30, 22, 98, 106), radius=6, outline=col, width=6)
        for y in (44, 64, 84):
            d.line((44, y, 84 if y < 84 else 68, y), fill=col, width=5)
    elif name == "icon_intel":
        d.arc((22, 34, 106, 94), start=180, end=360, fill=col, width=6)
        d.arc((22, 34, 106, 94), start=0, end=180, fill=col, width=6)
        d.ellipse((cx - 14, cy - 14, cx + 14, cy + 14), fill=col)
    elif name == "icon_roster":
        d.ellipse((34, 28, 62, 56), outline=col, width=6)
        d.arc((24, 64, 72, 110), start=180, end=360, fill=col, width=6)
        d.ellipse((74, 34, 96, 56), outline=col, width=5)
        d.arc((66, 68, 104, 106), start=180, end=360, fill=col, width=5)
    elif name == "icon_kit":
        d.rounded_rectangle((26, 40, 102, 98), radius=8, outline=col, width=6)
        d.rectangle((48, 24, 80, 40), outline=col, width=6)
        d.line((26, 66, 102, 66), fill=col, width=5)
    elif name == "icon_team":
        pts = [(cx + math.cos(k * math.pi / 3 - math.pi / 2) * 38, cy + math.sin(k * math.pi / 3 - math.pi / 2) * 38) for k in range(6)]
        d.polygon(pts, outline=col, width=6)
        d.ellipse((cx - 14, cy - 14, cx + 14, cy + 14), fill=col)
    elif name == "icon_play":
        d.polygon([(44, 30), (96, cy), (44, 98)], fill=col)
    elif name == "icon_pause":
        d.rounded_rectangle((38, 30, 56, 98), radius=4, fill=col)
        d.rounded_rectangle((72, 30, 90, 98), radius=4, fill=col)
    elif name == "icon_rewind":
        d.polygon([(64, 34), (28, cy), (64, 94)], fill=col)
        d.polygon([(100, 34), (64, cy), (100, 94)], fill=col)
    elif name == "icon_shield":
        d.polygon([(cx, 20), (96, 34), (96, 66), (cx, 108), (32, 66), (32, 34)], outline=col, width=6)
        d.line((cx, 32, cx, 94), fill=col, width=5)
    elif name == "icon_target":
        d.ellipse((30, 30, 98, 98), outline=col, width=6)
        d.ellipse((cx - 10, cy - 10, cx + 10, cy + 10), fill=col)
        for p in ((cx, 16, cx, 38), (cx, 90, cx, 112), (16, cy, 38, cy), (90, cy, 112, cy)):
            d.line(p, fill=col, width=6)
    elif name == "icon_waypoint":
        d.ellipse((34, 20, 94, 80), outline=col, width=6)
        d.polygon([(40, 68), (88, 68), (cx, 108)], fill=col)
        d.ellipse((cx - 10, 40, cx + 10, 60), fill=col)
    elif name == "icon_lock":
        d.rounded_rectangle((34, 56, 94, 102), radius=8, outline=col, width=6)
        d.arc((44, 26, 84, 72), start=180, end=360, fill=col, width=6)
        d.ellipse((cx - 8, 72, cx + 8, 88), fill=col)
    elif name == "icon_lan_coop":
        d.rounded_rectangle((22, 26, 56, 54), radius=4, outline=col, width=5)
        d.rounded_rectangle((72, 74, 106, 102), radius=4, outline=col, width=5)
        d.line((56, 40, 88, 40, 88, 74), fill=col, width=5)
        d.line((40, 54, 40, 88, 72, 88), fill=col, width=5)

    return img.resize((size, size), Image.Resampling.LANCZOS)


def write_wav(path: Path, samples: list[float], sr: int = 44100) -> None:
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        frames = bytearray()
        for v in samples:
            clamped = max(-1.0, min(1.0, v))
            frames.extend(struct.pack("<h", int(clamped * 32767)))
        wf.writeframes(bytes(frames))


def generate_sfx() -> list[dict]:
    sr = 44100
    rng = random.Random(SEED + 999)
    specs: list[dict] = []

    def gen(name: str, dur: float, fn) -> None:
        n = int(sr * dur)
        data = [fn(i / sr, dur) for i in range(n)]
        p = ROOT / "tacplanshooter/audio/sfx" / f"{name}.wav"
        write_wav(p, data, sr)
        specs.append({"path": f"tacplanshooter/audio/sfx/{name}.wav", "category": "audio_sfx", "sample_rate": sr, "duration_sec": dur})

    gen("ui_click_tactical", 0.055, lambda t, d: math.sin(2 * math.pi * (1400 - 600 * (t / d)) * t) * math.exp(-t * 65) * 0.6)
    gen("ui_waypoint_place", 0.11, lambda t, d: (math.sin(2 * math.pi * 880 * t) + 0.5 * math.sin(2 * math.pi * 1320 * t)) * math.exp(-t * 28) * 0.5)
    gen("ui_confirm_go", 0.18, lambda t, d: (math.sin(2 * math.pi * (660 if t < 0.07 else 990) * t)) * math.exp(-t * 14) * 0.55)
    gen("ui_error_blocked", 0.20, lambda t, d: (math.sin(2 * math.pi * 190 * t) + 0.4 * math.sin(2 * math.pi * 245 * t)) * math.exp(-t * 12) * 0.6)
    gen("sfx_suppressed_shot", 0.14, lambda t, d: (rng.uniform(-1, 1) * math.exp(-t * 48) * 0.7 + math.sin(2 * math.pi * (320 - 220 * (t / d)) * t) * math.exp(-t * 36) * 0.5))
    gen("sfx_breach_charge", 0.42, lambda t, d: (rng.uniform(-1, 1) * math.exp(-t * 9) * 0.75 + math.sin(2 * math.pi * (95 - 55 * (t / d)) * t) * math.exp(-t * 7) * 0.65))
    gen("sfx_flashbang_pop", 0.30, lambda t, d: (rng.uniform(-1, 1) * math.exp(-t * 18) * 0.75 + math.sin(2 * math.pi * 3200 * t) * math.exp(-t * 10) * 0.35))
    gen("sfx_door_unlock", 0.16, lambda t, d: (math.sin(2 * math.pi * (520 if t < 0.06 else 780) * t) * math.exp(-abs(t - (0.03 if t < 0.06 else 0.10)) * 55) * 0.6))
    return specs


def write_shaders() -> list[dict]:
    shaders = {
        "tactical_fog_of_war.gdshader": """shader_type canvas_item;

uniform sampler2D noise_tex : repeat_enable;
uniform vec4 fog_color : source_color = vec4(0.05, 0.07, 0.10, 0.88);
uniform float scroll_speed = 0.02;
uniform float density : hint_range(0.0, 1.0) = 0.85;

void fragment() {
    vec2 uv1 = UV + vec2(TIME * scroll_speed, TIME * scroll_speed * 0.4);
    vec2 uv2 = UV - vec2(TIME * scroll_speed * 0.6, TIME * scroll_speed * 0.25);
    float n = (texture(noise_tex, uv1).r + texture(noise_tex, uv2).r) * 0.5;
    vec4 base = texture(TEXTURE, UV);
    float alpha = clamp(base.a * density * (0.75 + n * 0.35), 0.0, 1.0);
    COLOR = vec4(fog_color.rgb, alpha * fog_color.a);
}
""",
        "tactical_hit_flash.gdshader": """shader_type canvas_item;

uniform float flash_amount : hint_range(0.0, 1.0) = 0.0;
uniform vec4 flash_color : source_color = vec4(1.0, 0.92, 0.82, 1.0);

void fragment() {
    vec4 tex = texture(TEXTURE, UV);
    vec3 mixed = mix(tex.rgb, flash_color.rgb, flash_amount);
    COLOR = vec4(mixed, tex.a);
}
""",
        "tactical_blueprint_grid.gdshader": """shader_type canvas_item;

uniform float cell_size = 64.0;
uniform float line_thickness = 1.5;
uniform vec4 line_color : source_color = vec4(0.0, 0.898, 1.0, 0.18);
uniform vec2 grid_offset = vec2(0.0, 0.0);

void fragment() {
    vec2 pos = (UV / TEXTURE_PIXEL_SIZE) + grid_offset;
    vec2 cell = mod(pos, cell_size);
    float lx = step(cell.x, line_thickness);
    float ly = step(cell.y, line_thickness);
    float mask = clamp(lx + ly, 0.0, 1.0);
    COLOR = vec4(line_color.rgb, line_color.a * mask);
}
""",
        "tactical_selection_pulse.gdshader": """shader_type canvas_item;

uniform vec4 ring_color : source_color = vec4(0.0, 0.898, 1.0, 1.0);
uniform float pulse_speed = 3.2;
uniform float ring_radius : hint_range(0.1, 0.48) = 0.38;
uniform float ring_width : hint_range(0.01, 0.15) = 0.06;

void fragment() {
    vec2 centered = UV - vec2(0.5);
    float dist = length(centered);
    float pulse = 0.5 + 0.5 * sin(TIME * pulse_speed);
    float r = ring_radius + pulse * 0.03;
    float edge = 1.0 - smoothstep(ring_width * 0.5, ring_width, abs(dist - r));
    COLOR = vec4(ring_color.rgb, edge * (0.65 + 0.35 * pulse));
}
""",
    }
    out = []
    for fname, body in shaders.items():
        (ROOT / "tacplanshooter/shaders" / fname).write_text(body, encoding="utf-8")
        out.append({"path": f"tacplanshooter/shaders/{fname}", "category": "shader", "renderer": "gl_compatibility"})
    return out


def write_theme() -> dict:
    tres = """[gd_resource type="Theme" load_steps=5 format=3]

[sub_resource type="StyleBoxFlat" id="StyleBoxFlat_panel"]
bg_color = Color(0.0509804, 0.0666667, 0.0901961, 0.94)
border_width_left = 2
border_width_top = 2
border_width_right = 2
border_width_bottom = 2
border_color = Color(0.188235, 0.211765, 0.239216, 1)
corner_radius_top_left = 6
corner_radius_top_right = 6
corner_radius_bottom_right = 6
corner_radius_bottom_left = 6
content_margin_left = 12.0
content_margin_top = 10.0
content_margin_right = 12.0
content_margin_bottom = 10.0

[sub_resource type="StyleBoxFlat" id="StyleBoxFlat_btn_normal"]
bg_color = Color(0.0862745, 0.105882, 0.133333, 1)
border_width_left = 2
border_width_top = 2
border_width_right = 2
border_width_bottom = 2
border_color = Color(0, 0.54902, 0.666667, 1)
corner_radius_top_left = 4
corner_radius_top_right = 4
corner_radius_bottom_right = 4
corner_radius_bottom_left = 4
content_margin_left = 14.0
content_margin_top = 8.0
content_margin_right = 14.0
content_margin_bottom = 8.0

[sub_resource type="StyleBoxFlat" id="StyleBoxFlat_btn_hover"]
bg_color = Color(0.129412, 0.14902, 0.176471, 1)
border_width_left = 2
border_width_top = 2
border_width_right = 2
border_width_bottom = 2
border_color = Color(0, 0.898039, 1, 1)
corner_radius_top_left = 4
corner_radius_top_right = 4
corner_radius_bottom_right = 4
corner_radius_bottom_left = 4

[sub_resource type="StyleBoxFlat" id="StyleBoxFlat_btn_pressed"]
bg_color = Color(0, 0.898039, 1, 0.2)
border_width_left = 2
border_width_top = 2
border_width_right = 2
border_width_bottom = 2
border_color = Color(1, 0.701961, 0, 1)
corner_radius_top_left = 4
corner_radius_top_right = 4
corner_radius_bottom_right = 4
corner_radius_bottom_left = 4

[resource]
default_font_size = 16
Button/colors/font_color = Color(0.921569, 0.945098, 0.968627, 1)
Button/colors/font_hover_color = Color(0, 0.898039, 1, 1)
Button/colors/font_pressed_color = Color(1, 0.701961, 0, 1)
Button/styles/hover = SubResource("StyleBoxFlat_btn_hover")
Button/styles/normal = SubResource("StyleBoxFlat_btn_normal")
Button/styles/pressed = SubResource("StyleBoxFlat_btn_pressed")
Label/colors/font_color = Color(0.862745, 0.894118, 0.929412, 1)
PanelContainer/styles/panel = SubResource("StyleBoxFlat_panel")
"""
    p = ROOT / "tacplanshooter/ui/themes/tactical_hud_theme.tres"
    p.write_text(tres, encoding="utf-8")
    return {"path": "tacplanshooter/ui/themes/tactical_hud_theme.tres", "category": "ui_theme", "engine": "Godot 4.0+"}


def wall_collision_polygon(idx: int) -> str | None:
    if idx == 12:
        return None
    polys = {
        0: "-32, -12, 32, -12, 32, 12, -32, 12",
        1: "-12, -32, 12, -32, 12, 32, -12, 32",
        2: "-12, -12, 32, -12, 32, 32, -12, 32",
        3: "-32, -12, 12, -12, 12, 32, -32, 32",
        4: "-12, -32, 32, -32, 32, 12, -12, 12",
        5: "-32, -32, 12, -32, 12, 12, -32, 12",
        6: "-32, -12, 32, -12, 32, 32, -32, 32",
        7: "-32, -32, 32, -32, 32, 32, -32, 32",
        8: "-18, -18, 18, -18, 18, 18, -18, 18",
        9: "-32, -6, 32, -6, 32, 6, -32, 6",
        10: "-6, -32, 6, -32, 6, 32, -6, 32",
        11: "-32, -12, 32, -12, 32, 12, -32, 12",
        13: "-32, -12, 32, -12, 32, 12, -32, 12",
        14: "-32, -12, 32, -12, 32, 12, -32, 12",
        15: "-32, -12, 32, -12, 32, 12, -32, 12",
        16: "-27, -17, 27, -17, 27, 17, -27, 17",
        17: "-22, -13, 22, -13, 22, 13, -22, 13",
        18: "-27, -22, 27, -22, 27, 22, -27, 22",
        19: "-24, -26, 24, -26, 24, 26, -24, 26",
        20: "-23, -23, 23, -23, 23, 23, -23, 23",
        21: "-22, -22, 22, -22, 22, 22, -22, 22",
        22: "-23, -18, 23, -18, 23, 18, -23, 18",
    }
    return polys.get(idx, "-19, -19, 19, -19, 19, 19, -19, 19")


def write_tileset_tres() -> dict:
    floor_lines = [f"{i % 8}:{i // 8}/0 = 0" for i in range(32)]
    wall_lines: list[str] = []
    for i in range(32):
        cx, cy = i % 8, i // 8
        wall_lines.append(f"{cx}:{cy}/0 = 0")
        poly = wall_collision_polygon(i)
        if poly is not None:
            wall_lines.append(f"{cx}:{cy}/0/physics_layer_0/linear_velocity = Vector2(0, 0)")
            wall_lines.append(f"{cx}:{cy}/0/physics_layer_0/angular_velocity = 0.0")
            wall_lines.append(f"{cx}:{cy}/0/physics_layer_0/polygon_0/points = PackedVector2Array({poly})")

    tres = (
        '[gd_resource type="TileSet" load_steps=5 format=3]\n\n'
        '[ext_resource type="Texture2D" path="res://tacplanshooter/tilesets/penthouse_floors_tileset.png" id="1_floors"]\n'
        '[ext_resource type="Texture2D" path="res://tacplanshooter/tilesets/tactical_walls_cover_tileset.png" id="2_walls"]\n\n'
        '[sub_resource type="TileSetAtlasSource" id="TileSetAtlasSource_floors"]\n'
        'resource_name = "PenthouseFloors"\n'
        'texture = ExtResource("1_floors")\n'
        'texture_region_size = Vector2i(64, 64)\n'
        + "\n".join(floor_lines)
        + "\n\n"
        '[sub_resource type="TileSetAtlasSource" id="TileSetAtlasSource_walls"]\n'
        'resource_name = "TacticalWallsCover"\n'
        'texture = ExtResource("2_walls")\n'
        'texture_region_size = Vector2i(64, 64)\n'
        + "\n".join(wall_lines)
        + "\n\n"
        "[resource]\n"
        "tile_size = Vector2i(64, 64)\n"
        "physics_layer_0/collision_layer = 1\n"
        "physics_layer_0/collision_mask = 0\n"
        'sources/0 = SubResource("TileSetAtlasSource_floors")\n'
        'sources/1 = SubResource("TileSetAtlasSource_walls")\n'
    )
    p = ROOT / "tacplanshooter/resources/penthouse_tileset.tres"
    p.write_text(tres, encoding="utf-8")
    return {"path": "tacplanshooter/resources/penthouse_tileset.tres", "category": "godot_tileset", "tile_size": 64, "collision_layers": 1}


def write_sprite_frames(
    out_name: str,
    texture_res_path: str,
    anims: list[tuple[str, list[tuple[int, int]], float, bool]],
) -> dict:
    sub_blocks: list[str] = []
    coord_to_id: dict[tuple[int, int], str] = {}
    for _, frames, _, _ in anims:
        for cx, cy in frames:
            if (cx, cy) not in coord_to_id:
                sid = f"AtlasTexture_{cx}_{cy}"
                coord_to_id[(cx, cy)] = sid
                sub_blocks.append(
                    f'[sub_resource type="AtlasTexture" id="{sid}"]\n'
                    'atlas = ExtResource("1_sheet")\n'
                    f"region = Rect2({cx * 64}, {cy * 64}, 64, 64)\n"
                )

    anim_blocks: list[str] = []
    for anim_name, frames, speed, loop in anims:
        frame_items = ", ".join(
            '{\n"duration": 1.0,\n"texture": SubResource("' + coord_to_id[c] + '")\n}'
            for c in frames
        )
        loop_str = "true" if loop else "false"
        anim_blocks.append(
            "{\n"
            f'"frames": [{frame_items}],\n'
            f'"loop": {loop_str},\n'
            f'"name": &"{anim_name}",\n'
            f'"speed": {speed:.1f}\n'
            "}"
        )

    load_steps = 1 + len(sub_blocks) + 1
    tres = (
        f'[gd_resource type="SpriteFrames" load_steps={load_steps} format=3]\n\n'
        f'[ext_resource type="Texture2D" path="{texture_res_path}" id="1_sheet"]\n\n'
        + "\n".join(sub_blocks)
        + "\n[resource]\nanimations = ["
        + ", ".join(anim_blocks)
        + "]\n"
    )
    p = ROOT / "tacplanshooter/resources" / out_name
    p.write_text(tres, encoding="utf-8")
    return {"path": f"tacplanshooter/resources/{out_name}", "category": "godot_spriteframes", "animations": len(anims)}


def write_godot_resources() -> list[dict]:
    out = [write_tileset_tres()]

    op_roles = ["pointman", "breacher", "recon", "shield"]
    op_states = ["idle", "aim", "move", "crouch"]
    op_anims = [
        (f"{role}_{st}", [(col, row)], 6.0, True)
        for row, role in enumerate(op_roles)
        for col, st in enumerate(op_states)
    ]
    out.append(write_sprite_frames("operators_frames.tres", "res://tacplanshooter/sprites/operators_sheet.png", op_anims))

    host_roles = ["guard", "enforcer", "heavy", "hvt"]
    host_states = ["idle", "alert", "aim", "down"]
    host_anims = [
        (f"{role}_{st}", [(col, row)], 6.0, st != "down")
        for row, role in enumerate(host_roles)
        for col, st in enumerate(host_states)
    ]
    out.append(write_sprite_frames("hostiles_frames.tres", "res://tacplanshooter/sprites/hostiles_sheet.png", host_anims))

    prop_anims = [
        ("flashbang", [(0, 0)], 1.0, False),
        ("smoke_grenade", [(1, 0)], 1.0, False),
        ("breach_charge", [(2, 0)], 1.0, False),
        ("medkit", [(3, 0)], 1.0, False),
        ("intel_briefcase", [(0, 1)], 1.0, False),
        ("keycard", [(1, 1)], 1.0, False),
        ("waypoint_ring", [(2, 1)], 1.0, True),
        ("target_lock", [(3, 1)], 1.0, True),
        ("muzzle_flash", [(0, 2), (1, 2), (2, 2)], 18.0, False),
        ("smoke_puff", [(3, 2), (0, 3), (1, 3)], 8.0, False),
        ("spark_burst", [(2, 3)], 12.0, False),
        ("scorch_decal", [(3, 3)], 1.0, False),
    ]
    out.append(write_sprite_frames("props_fx_frames.tres", "res://tacplanshooter/sprites/props_and_fx_sheet.png", prop_anims))
    return out


def write_root_docs(manifest_entries: list[dict]) -> None:
    (ROOT / ".gitignore").write_text(
        ".godot/\n*.import\n__pycache__/\n*.pyc\n.DS_Store\nThumbs.db\n",
        encoding="utf-8",
    )
    (ROOT / "LICENSE").write_text(
        "MIT License (Code & Shaders) / CC0 1.0 Universal (2D Art, Tilesets, Sprites, Icons, Audio)\n\n"
        "Copyright (c) 2026 GhostMan612\n\n"
        "Permission is hereby granted, free of charge, to any person obtaining a copy of this repository "
        "to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the assets and code.\n",
        encoding="utf-8",
    )
    (ROOT / "manifest.json").write_text(
        json.dumps(
            {
                "vault": "godot4-asset-vault",
                "target_engine": "Godot 4.0+ (gl_compatibility / OpenGL ES 3.0, msaa_2d=0)",
                "asset_count": len(manifest_entries),
                "assets": manifest_entries,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    readme = """# Godot 4 Asset Vault

Shared, deterministic 2D/UI/shader/audio asset repository for **GhostMan612** Godot 4 games and companion apps.

## Initial Drop: `tacplanshooter/`

Built specifically for **TacPlanShooter** (Godot 4.0, `gl_compatibility` OpenGL ES 3.0, `msaa_2d=0`, portrait Android):

| Folder | Contents |
| --- | --- |
| `tacplanshooter/tilesets/` | `penthouse_floors_tileset.png` (512x256, 8x4 x 64px) & `tactical_walls_cover_tileset.png` (512x256, 8x4 x 64px) |
| `tacplanshooter/resources/` | Ready-to-drop Godot 4.0 `.tres` resources: `penthouse_tileset.tres` (collision polygons pre-wired on physics layer 0), `operators_frames.tres`, `hostiles_frames.tres`, `props_fx_frames.tres` |
| `tacplanshooter/textures/` | 5 seamless 256x256 textures (concrete, penthouse hardwood, metal grate, tactical blueprint grid overlay, fog-of-war value noise) |
| `tacplanshooter/sprites/` | `operators_sheet.png`, `hostiles_sheet.png`, `props_and_fx_sheet.png` (each 256x256, 4x4 x 64px, `+X` Godot 2D forward orientation) |
| `tacplanshooter/ui/icons/` | 20 tactical UI icons in both 64x64 PNG and scalable SVG (`DRAW`/`TAP`, Breach, Flashbang, Smoke, Stairs Up/Down, Briefing/Intel/Roster/Kit/Team, Replay controls, LAN Co-op, Shield, Target, Waypoint, Lock) |
| `tacplanshooter/ui/themes/` | `tactical_hud_theme.tres` dark slate/cyan/amber Godot 4 UI theme |
| `tacplanshooter/shaders/` | 4 `gl_compatibility`-safe `canvas_item` shaders (fog of war, hit flash, blueprint grid, selection pulse) |
| `tacplanshooter/audio/sfx/` | 8 mono 16-bit 44.1 kHz WAV tactical UI & gameplay SFX |

## Godot 4 Import Notes

- **Drop-in `.tres` Resources:** Copy the `tacplanshooter/` folder into your Godot project root so `res://tacplanshooter/...` paths resolve automatically. `penthouse_tileset.tres` maps physics collision layer 0 to all solid walls, closed doors, pillars, and cover while leaving floor tiles and open doorways walkable.
- **Sprites & Tilesets:** Import with `Mipmaps: Off`, `Filter: Linear` (or `Nearest` for crisp pixel lock), `Compress Mode: Lossless` for UI icons and `VRAM Compressed` for 256x256 seamless floor textures.
- **Shaders:** All `.gdshader` files use pure `canvas_item` math with zero MSAA or Forward+ dependencies.

## Regenerating Assets

```bash
pip install pillow
python3 tools/bootstrap_vault.py
```

All outputs are indexed in `manifest.json`.
"""
    (ROOT / "README.md").write_text(readme, encoding="utf-8")


def main() -> None:
    ensure_dirs()
    entries: list[dict] = []

    floors = Image.new("RGBA", (512, 256), (0, 0, 0, 0))
    for i in range(32):
        floors.paste(draw_floor_tile(i, 64), ((i % 8) * 64, (i // 8) * 64))
    floors.save(ROOT / "tacplanshooter/tilesets/penthouse_floors_tileset.png")
    entries.append({"path": "tacplanshooter/tilesets/penthouse_floors_tileset.png", "category": "tileset", "size": "512x256", "tile_size": 64, "count": 32})

    walls = Image.new("RGBA", (512, 256), (0, 0, 0, 0))
    for i in range(32):
        walls.paste(draw_wall_cover_tile(i, 64), ((i % 8) * 64, (i // 8) * 64))
    walls.save(ROOT / "tacplanshooter/tilesets/tactical_walls_cover_tileset.png")
    entries.append({"path": "tacplanshooter/tilesets/tactical_walls_cover_tileset.png", "category": "tileset", "size": "512x256", "tile_size": 64, "count": 32})

    tex_builders = {
        "concrete_seamless_256.png": make_seamless_concrete,
        "hardwood_penthouse_256.png": make_seamless_hardwood,
        "metal_grate_seamless_256.png": make_seamless_grate,
        "tactical_grid_overlay_256.png": make_tactical_grid_overlay,
        "fog_noise_256.png": make_fog_noise,
    }
    for fname, fn in tex_builders.items():
        fn(256).save(ROOT / "tacplanshooter/textures" / fname)
        entries.append({"path": f"tacplanshooter/textures/{fname}", "category": "texture", "size": "256x256", "seamless": True})

    ops = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    hostiles = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    for r in range(4):
        for st in range(4):
            ops.paste(draw_character_sprite(False, r, st, 64), (st * 64, r * 64))
            hostiles.paste(draw_character_sprite(True, r, st, 64), (st * 64, r * 64))
    ops.save(ROOT / "tacplanshooter/sprites/operators_sheet.png")
    hostiles.save(ROOT / "tacplanshooter/sprites/hostiles_sheet.png")
    entries.append({"path": "tacplanshooter/sprites/operators_sheet.png", "category": "spritesheet", "size": "256x256", "frame_size": 64, "grid": "4x4"})
    entries.append({"path": "tacplanshooter/sprites/hostiles_sheet.png", "category": "spritesheet", "size": "256x256", "frame_size": 64, "grid": "4x4"})

    props = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    for i in range(16):
        props.paste(draw_prop_fx(i, 64), ((i % 4) * 64, (i // 4) * 64))
    props.save(ROOT / "tacplanshooter/sprites/props_and_fx_sheet.png")
    entries.append({"path": "tacplanshooter/sprites/props_and_fx_sheet.png", "category": "spritesheet", "size": "256x256", "frame_size": 64, "grid": "4x4"})

    for name, (color_hex, inner_svg) in SVG_ICONS.items():
        svg_str = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">'
            f'<rect x="3" y="3" width="58" height="58" rx="9" fill="#141A22" stroke="{color_hex}" stroke-width="2"/>'
            + inner_svg.format(c=color_hex)
            + "</svg>\n"
        )
        (ROOT / "tacplanshooter/ui/icons" / f"{name}.svg").write_text(svg_str, encoding="utf-8")
        render_icon_png(name, color_hex, 64).save(ROOT / "tacplanshooter/ui/icons" / f"{name}.png")
        entries.append({"path": f"tacplanshooter/ui/icons/{name}.png", "category": "ui_icon_png", "size": "64x64"})
        entries.append({"path": f"tacplanshooter/ui/icons/{name}.svg", "category": "ui_icon_svg", "viewbox": "64x64"})

    entries.extend(write_godot_resources())
    entries.append(write_theme())
    entries.extend(write_shaders())
    entries.extend(generate_sfx())
    write_root_docs(entries)
    print(f"Generated {len(entries)} assets cleanly in {ROOT}")


if __name__ == "__main__":
    main()
