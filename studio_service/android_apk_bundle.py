# As Above, So Below. As Within, So Without.
# The Future Dictates the Past and the Past is Always Present.

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
import urllib.error
import urllib.request
import wave
import zipfile
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from studio_service.foundry_config import FoundryConfig
from studio_service.tcs_audio_bridge import request_tcs_audio

BUNDLES_DIR = ROOT / "generated_bundles"

MIPMAP_SIZES = {
    "mipmap-mdpi": 48,
    "mipmap-hdpi": 72,
    "mipmap-xhdpi": 96,
    "mipmap-xxhdpi": 144,
    "mipmap-xxxhdpi": 192,
}

PLAY_STORE_SPECS = {
    "play_store/app_icon_512.png": (512, 512, "RGBA"),
    "play_store/feature_graphic_1024x500.png": (1024, 500, "RGB"),
    "play_store/screenshots/phone_01_title.png": (1080, 1920, "RGB"),
    "play_store/screenshots/phone_02_menu.png": (1080, 1920, "RGB"),
    "play_store/screenshots/tablet7_01_title.png": (1200, 1920, "RGB"),
    "play_store/screenshots/tablet10_01_title.png": (1600, 2560, "RGB"),
}

ADAPTIVE_ICON_XML = """<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@mipmap/ic_launcher_background" />
    <foreground android:drawable="@mipmap/ic_launcher_foreground" />
    <monochrome android:drawable="@mipmap/ic_launcher_monochrome" />
</adaptive-icon>
"""


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", text.lower()).strip("_") or "android_app"


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    cleaned = hex_color.lstrip("#")
    if len(cleaned) != 6:
        return (28, 34, 48)
    return (int(cleaned[0:2], 16), int(cleaned[2:4], 16), int(cleaned[4:6], 16))


def _ollama_chat(cfg: FoundryConfig, system_prompt: str, user_prompt: str, timeout: int = 12) -> str | None:
    payload = {
        "model": cfg.ollama_model,
        "temperature": 0.25,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    try:
        req = urllib.request.Request(
            f"{cfg.ollama_url.rstrip('/')}/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return str(data["choices"][0]["message"]["content"])
    except (urllib.error.URLError, TimeoutError, KeyError, IndexError, json.JSONDecodeError, OSError):
        return None


def expand_brief_via_local_llm(app_name: str, genre: str, brief: str, cfg: FoundryConfig | None = None) -> dict:
    c = cfg or FoundryConfig()
    default_palette = {
        "primary": "#141824",
        "secondary": "#26324A",
        "accent": "#E6A23C",
        "highlight": "#4FD1C5",
        "mood": genre or "dark tactical",
        "tagline": brief[:72] if brief else f"{app_name} — Android Edition",
        "source": "default",
    }
    content = _ollama_chat(
        c,
        "Return strict JSON with keys primary, secondary, accent, highlight (6-digit hex colors), mood, and tagline (max 60 chars).",
        f"App: {app_name}. Genre: {genre}. Brief: {brief}",
    )
    if content:
        match = re.search(r"\{.*\}", content, flags=re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(0))
                for key in ("primary", "secondary", "accent", "highlight", "mood", "tagline"):
                    if isinstance(parsed.get(key), str) and parsed[key].strip():
                        default_palette[key] = parsed[key].strip()
                default_palette["source"] = f"ollama:{c.ollama_model}@{c.ollama_url}"
            except json.JSONDecodeError:
                pass
    return default_palette


def generate_svg_emblem_via_ollama(
    app_name: str,
    genre: str,
    palette: dict,
    size: int,
    svg_out_path: Path,
    cfg: FoundryConfig | None = None,
) -> tuple[Image.Image | None, str]:
    c = cfg or FoundryConfig()
    content = _ollama_chat(
        c,
        (
            "Output ONLY a single valid standalone SVG element (<svg xmlns=\"http://www.w3.org/2000/svg\" "
            "viewBox=\"0 0 512 512\">...</svg>) with transparent background, bold centered geometric app emblem "
            "inside the central 320x320 safe zone, no text elements, no external links."
        ),
        f"App: {app_name}. Genre: {genre}. Accent: {palette['accent']}. Highlight: {palette['highlight']}.",
        timeout=15,
    )
    if not content:
        return None, "procedural"
    match = re.search(r"<svg\b[^>]*>.*?</svg>", content, flags=re.DOTALL | re.IGNORECASE)
    if not match:
        return None, "procedural"
    svg_text = match.group(0)
    svg_out_path.parent.mkdir(parents=True, exist_ok=True)
    svg_out_path.write_text(svg_text, encoding="utf-8")

    try:
        import cairosvg

        png_bytes = cairosvg.svg2png(bytestring=svg_text.encode("utf-8"), output_width=size, output_height=size)
        img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
        return img, f"ollama_svg:{c.ollama_model}"
    except Exception:
        return None, "procedural_svg_saved"


def render_gradient_backdrop(
    width: int,
    height: int,
    c_top: tuple[int, int, int],
    c_bot: tuple[int, int, int],
    accent: tuple[int, int, int],
    seed: int = 1,
) -> Image.Image:
    y = np.linspace(0.0, 1.0, height, dtype=np.float32)[:, None]
    x = np.linspace(0.0, 1.0, width, dtype=np.float32)[None, :]
    top = np.array(c_top, dtype=np.float32)[None, None, :]
    bot = np.array(c_bot, dtype=np.float32)[None, None, :]
    img_arr = top * (1.0 - y[:, :, None]) + bot * y[:, :, None]

    cx, cy = 0.5, 0.38
    dist = np.sqrt((x - cx) ** 2 + ((y - cy) * (height / max(width, 1))) ** 2)
    glow = np.exp(-dist * 3.8)[:, :, None] * 0.35
    img_arr = np.clip(img_arr + np.array(accent, dtype=np.float32)[None, None, :] * glow, 0, 255)

    rng = np.random.default_rng(seed)
    grain = rng.normal(0.0, 2.2, size=(height, width, 1)).astype(np.float32)
    img_arr = np.clip(img_arr + grain, 0, 255).astype(np.uint8)
    return Image.fromarray(img_arr, mode="RGB")


def render_emblem_rgba(size: int, accent: tuple[int, int, int], highlight: tuple[int, int, int]) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    pad = int(size * 0.16)
    ring_w = max(4, size // 28)

    draw.ellipse((pad, pad, size - pad, size - pad), outline=(*accent, 255), width=ring_w)
    inner_pad = int(size * 0.25)
    draw.ellipse((inner_pad, inner_pad, size - inner_pad, size - inner_pad), outline=(*highlight, 220), width=max(2, ring_w // 2))

    cx, cy = size // 2, size // 2
    r = int(size * 0.24)
    diamond = [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]
    draw.polygon(diamond, fill=(*accent, 235), outline=(*highlight, 255))
    inner_r = int(size * 0.11)
    core = [(cx, cy - inner_r), (cx + inner_r, cy), (cx, cy + inner_r), (cx - inner_r, cy)]
    draw.polygon(core, fill=(245, 248, 255, 255))
    return img


def render_button_sheet(accent: tuple[int, int, int], secondary: tuple[int, int, int], highlight: tuple[int, int, int]) -> Image.Image:
    btn_w, btn_h = 320, 96
    sheet = Image.new("RGBA", (btn_w * 2, btn_h * 2), (0, 0, 0, 0))
    states = [
        (0, 0, secondary, accent, 255),
        (1, 0, accent, highlight, 255),
        (0, 1, secondary, highlight, 255),
        (1, 1, (65, 68, 76), (110, 114, 124), 190),
    ]
    for col, row, fill_rgb, border_rgb, alpha in states:
        tile = Image.new("RGBA", (btn_w, btn_h), (0, 0, 0, 0))
        d = ImageDraw.Draw(tile)
        d.rounded_rectangle(
            (8, 8, btn_w - 8, btn_h - 8),
            radius=18,
            fill=(*fill_rgb, alpha),
            outline=(*border_rgb, 255),
            width=4,
        )
        sheet.alpha_composite(tile, (col * btn_w, row * btn_h))
    return sheet


def apply_k_weighted_lufs_norm(samples: np.ndarray, sample_rate: int, target_lufs: float = -16.0) -> np.ndarray:
    x = samples.astype(np.float64)
    rc_hp = 1.0 / (2.0 * math.pi * 38.0)
    dt = 1.0 / sample_rate
    alpha_hp = rc_hp / (rc_hp + dt)
    hp = np.empty_like(x)
    hp[0] = x[0]
    for i in range(1, len(x)):
        hp[i] = alpha_hp * (hp[i - 1] + x[i] - x[i - 1])

    rms = float(np.sqrt(np.mean(hp ** 2) + 1e-12))
    current_lufs = -0.691 + 20.0 * math.log10(max(rms, 1e-9))
    gain_db = target_lufs - current_lufs
    scaled = x * (10.0 ** (gain_db / 20.0))

    peak = float(np.max(np.abs(scaled)) + 1e-12)
    ceiling = 10.0 ** (-1.0 / 20.0)
    if peak > ceiling:
        scaled = scaled * (ceiling / peak)
    return np.clip(scaled, -1.0, 1.0)


def write_wav_mono(path: Path, samples: np.ndarray, sample_rate: int = 44100, target_lufs: float = -16.0) -> None:
    mastered = apply_k_weighted_lufs_norm(samples, sample_rate, target_lufs=target_lufs)
    pcm = (mastered * 32767.0).astype(np.int16)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())


def synthesize_ui_sfx(kind: str, output_path: Path, sample_rate: int = 44100, cfg: FoundryConfig | None = None) -> dict:
    durations = {
        "tap": 0.08,
        "swipe": 0.18,
        "confirm": 0.22,
        "back": 0.16,
        "error": 0.28,
        "unlock": 0.42,
    }
    dur = durations.get(kind, 0.15)
    tcs_hit = request_tcs_audio(f"crisp mobile UI {kind} sound effect", "sfx", dur, output_path, cfg=cfg)
    if tcs_hit is not None:
        tcs_hit["kind"] = kind
        return tcs_hit

    t = np.linspace(0.0, dur, int(sample_rate * dur), endpoint=False, dtype=np.float64)
    if kind == "tap":
        sig = np.sin(2.0 * math.pi * (880.0 - 420.0 * (t / dur)) * t) * np.exp(-t * 48.0)
    elif kind == "swipe":
        rng = np.random.default_rng(7)
        noise = rng.normal(0.0, 1.0, size=len(t))
        sweep = np.sin(2.0 * math.pi * (240.0 + 960.0 * (t / dur)) * t)
        env = np.sin(math.pi * t / dur) ** 1.5
        sig = (0.45 * noise + 0.55 * sweep) * env
    elif kind == "confirm":
        sig = (
            np.sin(2.0 * math.pi * 523.25 * t) * np.exp(-t * 14.0)
            + np.sin(2.0 * math.pi * 783.99 * t) * np.clip((t - 0.05) * 20.0, 0.0, 1.0) * np.exp(-t * 10.0)
        )
    elif kind == "back":
        sig = np.sin(2.0 * math.pi * (520.0 - 220.0 * (t / dur)) * t) * np.exp(-t * 20.0)
    elif kind == "error":
        sig = (np.sign(np.sin(2.0 * math.pi * 155.0 * t)) * 0.45 + np.sin(2.0 * math.pi * 116.5 * t) * 0.55) * np.exp(-t * 9.0)
    else:
        sig = (
            np.sin(2.0 * math.pi * 440.0 * t)
            + 0.7 * np.sin(2.0 * math.pi * 659.25 * t)
            + 0.6 * np.sin(2.0 * math.pi * 880.0 * t)
        ) * np.exp(-t * 6.0)

    write_wav_mono(output_path, sig, sample_rate=sample_rate, target_lufs=-16.0)
    return {
        "engine": "numpy_lufs_synth",
        "kind": kind,
        "path": str(output_path),
        "duration_s": dur,
        "sample_rate": sample_rate,
        "target_lufs": -16.0,
    }


def synthesize_bgm_loop(
    track_type: str,
    output_path: Path,
    duration_s: float = 8.0,
    sample_rate: int = 44100,
    cfg: FoundryConfig | None = None,
) -> dict:
    tcs_hit = request_tcs_audio(
        f"seamless looping {track_type.replace('_', ' ')} game soundtrack",
        "bgm",
        duration_s,
        output_path,
        cfg=cfg,
    )
    if tcs_hit is not None:
        tcs_hit["track_type"] = track_type
        return tcs_hit

    t = np.linspace(0.0, duration_s, int(sample_rate * duration_s), endpoint=False, dtype=np.float64)
    roots = {"title_theme": 110.0, "menu_ambient": 82.41, "gameplay_bgm": 130.81}
    base_hz = roots.get(track_type, 110.0)

    pad = (
        0.45 * np.sin(2.0 * math.pi * base_hz * t)
        + 0.30 * np.sin(2.0 * math.pi * (base_hz * 1.5) * t)
        + 0.20 * np.sin(2.0 * math.pi * (base_hz * 1.1892) * t)
    )
    lfo = 0.65 + 0.35 * np.sin(2.0 * math.pi * (2.0 / duration_s) * t)
    pulse_rate = 4.0 if track_type == "gameplay_bgm" else 2.0
    pulse = np.maximum(0.0, np.sin(2.0 * math.pi * pulse_rate * t)) ** 4
    arp = np.sin(2.0 * math.pi * (base_hz * 2.0) * t) * pulse * 0.25

    sig = pad * lfo + arp
    fade_n = int(sample_rate * 0.04)
    sig[:fade_n] *= np.linspace(0.0, 1.0, fade_n)
    sig[-fade_n:] *= np.linspace(1.0, 0.0, fade_n)

    write_wav_mono(output_path, sig, sample_rate=sample_rate, target_lufs=-16.0)
    return {
        "engine": "numpy_lufs_synth",
        "track_type": track_type,
        "path": str(output_path),
        "duration_s": duration_s,
        "sample_rate": sample_rate,
        "target_lufs": -16.0,
    }


def generate_background_asset(
    app_name: str,
    theme_prompt: str,
    width: int,
    height: int,
    output_path: Path,
    palette: dict | None = None,
    cfg: FoundryConfig | None = None,
) -> dict:
    c = cfg or FoundryConfig()
    pal = palette or expand_brief_via_local_llm(app_name, theme_prompt, theme_prompt, cfg=c)
    backend = c.image_backend.strip().lower()
    if backend in ("comfyui", "diffusers"):
        try:
            sys.path.insert(0, str(ROOT / "tools"))
            import local_image_backend

            res = local_image_backend.generate_sheet_image(
                prompt=f"{app_name} {theme_prompt} background screen art",
                output_path=output_path,
                backend=backend,
                width=min(width, 1344),
                height=min(height, 1344),
                chroma_key=False,
            )
            with Image.open(output_path) as im:
                im.convert("RGB").resize((width, height), Image.Resampling.LANCZOS).save(output_path, format="PNG")
            return {"source": backend, "path": str(output_path), "width": width, "height": height, "meta": res}
        except Exception:
            pass

    img = render_gradient_backdrop(
        width,
        height,
        hex_to_rgb(pal["primary"]),
        hex_to_rgb(pal["secondary"]),
        hex_to_rgb(pal["accent"]),
        seed=abs(hash(f"{app_name}:{theme_prompt}")) % 10000,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, format="PNG")
    return {"source": "procedural_fallback", "path": str(output_path), "width": width, "height": height}


def validate_play_store_specs(stage_dir: Path) -> list[dict]:
    checks: list[dict] = []
    for rel_path, (exp_w, exp_h, exp_mode) in PLAY_STORE_SPECS.items():
        fp = stage_dir / rel_path
        if not fp.exists():
            raise FileNotFoundError(f"Missing Play Store asset: {rel_path}")
        with Image.open(fp) as im:
            ok = im.size == (exp_w, exp_h) and im.mode == exp_mode
            if not ok:
                raise ValueError(
                    f"Spec mismatch for {rel_path}: got {im.size} {im.mode}, expected {(exp_w, exp_h)} {exp_mode}"
                )
            checks.append(
                {
                    "file": rel_path,
                    "size": list(im.size),
                    "mode": im.mode,
                    "bytes": fp.stat().st_size,
                    "compliant": True,
                }
            )
    return checks


def generate_android_apk_package(
    app_name: str,
    package_id: str,
    genre: str = "tactical",
    brief: str = "",
    output_dir: Path | None = None,
    cfg: FoundryConfig | None = None,
) -> dict:
    c = cfg or FoundryConfig()
    slug = slugify(app_name)
    out_root = output_dir or BUNDLES_DIR
    out_root.mkdir(parents=True, exist_ok=True)

    palette = expand_brief_via_local_llm(app_name, genre, brief, cfg=c)
    c_primary = hex_to_rgb(palette["primary"])
    c_secondary = hex_to_rgb(palette["secondary"])
    c_accent = hex_to_rgb(palette["accent"])
    c_highlight = hex_to_rgb(palette["highlight"])

    with tempfile.TemporaryDirectory(prefix=f"apk_bundle_{slug}_") as tmp:
        stage = Path(tmp) / slug
        stage.mkdir(parents=True, exist_ok=True)

        icon_bg_512 = render_gradient_backdrop(512, 512, c_primary, c_secondary, c_accent, seed=11).convert("RGBA")
        svg_emblem, emblem_source = generate_svg_emblem_via_ollama(
            app_name,
            genre,
            palette,
            512,
            stage / "icons" / "app_emblem.svg",
            cfg=c,
        )
        emblem_512 = svg_emblem if svg_emblem is not None else render_emblem_rgba(512, c_accent, c_highlight)
        icon_full_512 = Image.alpha_composite(icon_bg_512, emblem_512)

        for folder, px in MIPMAP_SIZES.items():
            mdir = stage / "android" / "res" / folder
            mdir.mkdir(parents=True, exist_ok=True)
            icon_full_512.resize((px, px), Image.Resampling.LANCZOS).save(mdir / "ic_launcher.png")
            icon_full_512.resize((px, px), Image.Resampling.LANCZOS).save(mdir / "ic_launcher_round.png")
            icon_bg_512.resize((px, px), Image.Resampling.LANCZOS).save(mdir / "ic_launcher_background.png")
            emblem_512.resize((px, px), Image.Resampling.LANCZOS).save(mdir / "ic_launcher_foreground.png")
            mono = emblem_512.convert("L").resize((px, px), Image.Resampling.LANCZOS)
            mono_alpha = emblem_512.split()[3].resize((px, px), Image.Resampling.LANCZOS)
            Image.merge("RGBA", (mono, mono, mono, mono_alpha)).save(mdir / "ic_launcher_monochrome.png")

        anydpi = stage / "android" / "res" / "mipmap-anydpi-v26"
        anydpi.mkdir(parents=True, exist_ok=True)
        (anydpi / "ic_launcher.xml").write_text(ADAPTIVE_ICON_XML, encoding="utf-8")
        (anydpi / "ic_launcher_round.xml").write_text(ADAPTIVE_ICON_XML, encoding="utf-8")

        screens_dir = stage / "screens"
        screens_dir.mkdir(parents=True, exist_ok=True)
        title_portrait = render_gradient_backdrop(1080, 1920, c_primary, c_secondary, c_accent, seed=21)
        title_rgba = title_portrait.convert("RGBA")
        title_rgba.alpha_composite(emblem_512.resize((420, 420), Image.Resampling.LANCZOS), (330, 420))
        title_rgba.convert("RGB").save(screens_dir / "title_screen_1080x1920.png")

        menu_bg = render_gradient_backdrop(1080, 1920, c_secondary, c_primary, c_highlight, seed=22)
        menu_bg.save(screens_dir / "menu_screen_1080x1920.png")

        splash_mask = Image.new("RGBA", (1152, 1152), (0, 0, 0, 0))
        splash_mask.alpha_composite(emblem_512.resize((640, 640), Image.Resampling.LANCZOS), (256, 256))
        splash_mask.save(screens_dir / "android12_splash_mask_1152.png")

        ui_dir = stage / "ui"
        ui_dir.mkdir(parents=True, exist_ok=True)
        render_button_sheet(c_accent, c_secondary, c_highlight).save(ui_dir / "buttons_4state_sheet.png")

        ps_dir = stage / "play_store"
        ps_shots = ps_dir / "screenshots"
        ps_shots.mkdir(parents=True, exist_ok=True)
        icon_full_512.save(ps_dir / "app_icon_512.png")

        feat = render_gradient_backdrop(1024, 500, c_primary, c_secondary, c_accent, seed=31).convert("RGBA")
        feat.alpha_composite(emblem_512.resize((320, 320), Image.Resampling.LANCZOS), (352, 90))
        feat.convert("RGB").save(ps_dir / "feature_graphic_1024x500.png")

        title_rgba.convert("RGB").save(ps_shots / "phone_01_title.png")
        menu_bg.convert("RGB").save(ps_shots / "phone_02_menu.png")
        title_rgba.convert("RGB").resize((1200, 1920), Image.Resampling.LANCZOS).save(ps_shots / "tablet7_01_title.png")
        title_rgba.convert("RGB").resize((1600, 2560), Image.Resampling.LANCZOS).save(ps_shots / "tablet10_01_title.png")

        audio_dir = stage / "audio"
        sfx_records = [
            synthesize_ui_sfx(kind, audio_dir / "sfx" / f"ui_{kind}.wav", cfg=c)
            for kind in ("tap", "swipe", "confirm", "back", "error", "unlock")
        ]
        bgm_records = [
            synthesize_bgm_loop(track, audio_dir / "bgm" / f"{track}.wav", duration_s=8.0, cfg=c)
            for track in ("title_theme", "menu_ambient", "gameplay_bgm")
        ]

        play_store_checks = validate_play_store_specs(stage)
        manifest = {
            "app_name": app_name,
            "package_id": package_id,
            "genre": genre,
            "palette": palette,
            "emblem_source": emblem_source,
            "audio_engines": sorted({r["engine"] for r in sfx_records + bgm_records}),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "play_store_validation": play_store_checks,
            "audio_sfx_count": len(sfx_records),
            "audio_bgm_count": len(bgm_records),
        }
        (stage / "bundle_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

        zip_name = f"{slug}_android_playstore_bundle.zip"
        zip_path = out_root / zip_name
        file_count = 0
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            for fp in sorted(stage.rglob("*")):
                if fp.is_file():
                    zf.write(fp, fp.relative_to(stage).as_posix())
                    file_count += 1

    sha256 = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    return {
        "status": "ok",
        "zip_name": zip_name,
        "zip_path": str(zip_path),
        "file_count": file_count,
        "size_mb": round(zip_path.stat().st_size / (1024 * 1024), 2),
        "sha256": sha256,
        "play_store_compliant": True,
        "emblem_source": emblem_source,
        "audio_engines": manifest["audio_engines"],
        "palette": palette,
    }
