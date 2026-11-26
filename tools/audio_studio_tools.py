# As Above, So Below. As Within, So Without.
# The Future Dictates the Past and the Past is Always Present.

"""Framework-agnostic tool surface for the AI-assisted audio studio.

Each tool is a plain callable with a JSON Schema. A custom MCP server can
expose TOOLS directly; the CLI here is for local verification. Deterministic
tools work offline; generative tools degrade gracefully when their backend
is unavailable.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
import wave
from pathlib import Path
from typing import Callable

import numpy as np

ROOT = Path(__file__).resolve().parent.parent


def _ollama_base_url() -> str:
    value = os.environ.get("OLLAMA_HOST", "http://localhost:11434").strip()
    if "://" not in value:
        value = "http://" + value
    return value.rstrip("/")


OLLAMA_HOST = _ollama_base_url()


# ---------------------------------------------------------------------------
# Helpers

def _read_wav(path: Path) -> tuple[np.ndarray, int, int]:
    with wave.open(str(path), "rb") as wf:
        if wf.getsampwidth() != 2:
            raise ValueError("Only 16-bit PCM WAV is supported")
        rate, channels = wf.getframerate(), wf.getnchannels()
        data = np.frombuffer(wf.readframes(wf.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
    return (data.reshape(-1, channels) if channels > 1 else data), rate, channels


def _write_wav(path: Path, data: np.ndarray, rate: int) -> None:
    pcm = np.rint(np.clip(data, -1.0, 1.0) * 32767.0).astype("<i2")
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1 if pcm.ndim == 1 else pcm.shape[1])
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(pcm.tobytes())


def _biquad(x: np.ndarray, b0: float, b1: float, b2: float, a1: float, a2: float) -> np.ndarray:
    y = np.zeros_like(x)
    z1 = z2 = 0.0
    for i in range(len(x)):
        xi = float(x[i])
        yi = b0 * xi + z1
        z1 = b1 * xi - a1 * yi + z2
        z2 = b2 * xi - a2 * yi
        y[i] = yi
    return y


def _k_weight(x: np.ndarray, rate: int) -> np.ndarray:
    """BS.1770-style K-weighting: +4 dB shelf at 1.5 kHz and 38 Hz high-pass."""
    w0 = 2.0 * math.pi * 1500.0 / rate
    alpha = math.sin(w0) / (2.0 * math.sqrt(0.5))
    A = 10.0 ** (4.0 / 40.0)
    b0 = A * ((A + 1) + (A - 1) * math.cos(w0) + 2.0 * math.sqrt(A) * alpha)
    b1 = -2.0 * A * ((A - 1) + (A + 1) * math.cos(w0))
    b2 = A * ((A + 1) + (A - 1) * math.cos(w0) - 2.0 * math.sqrt(A) * alpha)
    a0 = (A + 1) - (A - 1) * math.cos(w0) + 2.0 * math.sqrt(A) * alpha
    a1 = 2.0 * ((A - 1) - (A + 1) * math.cos(w0))
    a2 = (A + 1) - (A - 1) * math.cos(w0) - 2.0 * math.sqrt(A) * alpha
    y = _biquad(x, b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0)

    w0 = 2.0 * math.pi * 38.0 / rate
    alpha = math.sin(w0) / (2.0 * math.sqrt(0.5))
    b0 = (1.0 + math.cos(w0)) / 2.0
    b1 = -(1.0 + math.cos(w0))
    b2 = b0
    a0 = 1.0 + alpha
    a1 = -2.0 * math.cos(w0)
    a2 = 1.0 - alpha
    return _biquad(y, b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0)


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _db_to_lin(db: float) -> float:
    return 10.0 ** (db / 20.0)


def _lin_to_db(value: float) -> float:
    return 20.0 * math.log10(max(value, 1e-9))


def _sanitize_cues(raw_cues: object, source_dir: Path) -> list[dict]:
    allowed_roles = {"sfx", "ui", "vox", "bgm", "ambience"}
    allowed_buses = {"SFX", "VOX", "Music", "Ambience"}
    bus_aliases = {"UI": "SFX", "MUSIC": "Music", "SFX": "SFX", "VOX": "VOX", "AMBIENCE": "Ambience"}
    sources = sorted(p.name for p in source_dir.glob("*.wav"))
    result: list[dict] = []
    if not isinstance(raw_cues, list):
        return result
    for idx, item in enumerate(raw_cues):
        if not isinstance(item, dict):
            continue
        source = str(item.get("source", ""))
        if source not in sources:
            source = sources[idx % len(sources)] if sources else str(item.get("source", ""))
        role = str(item.get("role", "sfx")).lower()
        if role not in allowed_roles:
            role = "ui" if source.startswith("ui_") else "sfx"
        bus = str(item.get("bus", "SFX")).upper()
        bus = bus_aliases.get(bus, str(item.get("bus", "SFX")))
        if bus not in allowed_buses:
            bus = "SFX"
        try:
            peak = float(item.get("target_peak_db", -1.5))
        except (TypeError, ValueError):
            peak = -1.5
        peak = max(-12.0, min(-1.0, peak))
        try:
            fade = int(item.get("fade_ms", 2))
        except (TypeError, ValueError):
            fade = 2
        fade = max(0, min(20, fade))
        cue_id = str(item.get("id", "")).strip() or f"cue_{idx + 1}"
        cue_id = "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in cue_id.lower())
        result.append(
            {
                "id": cue_id,
                "source": source,
                "role": role,
                "bus": bus,
                "target_peak_db": peak,
                "fade_ms": fade,
                "loop": bool(item.get("loop", False)),
            }
        )
    return result


def _ollama_generate(model: str, prompt: str) -> str | None:
    payload = json.dumps({"model": model, "prompt": prompt, "format": "json", "stream": False}).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_HOST}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        return str(body.get("response", ""))
    except (urllib.error.URLError, TimeoutError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Tools

def list_backends(arguments: dict) -> dict:
    available = {name: shutil.which(name) for name in ("ffmpeg", "sox", "piper", "ollama")}
    ollama_live = False
    try:
        with urllib.request.urlopen(f"{OLLAMA_HOST}/api/tags", timeout=3) as resp:
            ollama_live = resp.status == 200
    except (urllib.error.URLError, TimeoutError, ValueError):
        pass
    return {
        "status": "ok",
        "executables": {k: (v or "not found") for k, v in available.items()},
        "ollama_http": ollama_live,
        "note": "Deterministic DSP tools need no backend; generative tools do.",
    }


def generate_cue_sheet(arguments: dict) -> dict:
    brief = str(arguments["brief"])
    pack = str(arguments.get("pack", "vault"))
    source_dir = ROOT / str(arguments.get("source_dir", "tacplanshooter/audio/sfx"))
    output_dir = str(arguments.get("output_dir", f"{pack}/audio/packed"))
    use_llm = bool(arguments.get("use_llm", True))
    model = str(arguments.get("model", "qwen2.5:3b"))

    cue_list = None
    llm_used = False
    if use_llm:
        prompt = (
            "Return ONLY JSON: {\"cues\":[{\"id\":str,\"source\":str,\"role\":"
            "\"sfx\"|\"ui\"|\"vox\"|\"bgm\"|\"ambience\",\"bus\":"
            "\"SFX\"|\"VOX\"|\"Music\"|\"Ambience\",\"target_peak_db\":number,"
            "\"fade_ms\":number,\"loop\":bool}]}. "
            "Use only the listed source filenames. "
            "target_peak_db must be between -6.0 and -1.0. "
            "fade_ms must be an integer between 0 and 10. "
            "Bus must be exactly SFX, VOX, Music or Ambience. "
            f"Brief: {brief}. Source files: "
            + ", ".join(p.name for p in sorted(source_dir.glob("*.wav")))
        )
        raw = _ollama_generate(model, prompt)
        if raw:
            try:
                cleaned = raw.strip().removeprefix("```json").removesuffix("```").strip()
                cue_list = _sanitize_cues(json.loads(cleaned).get("cues"), source_dir)
                llm_used = bool(cue_list)
            except (ValueError, AttributeError):
                cue_list = None

    if not cue_list:
        cue_list = []
        for wav in sorted(source_dir.glob("*.wav")):
            role = "ui" if wav.name.startswith("ui_") else "sfx"
            cue_list.append(
                {
                    "id": wav.stem,
                    "source": wav.name,
                    "role": role,
                    "bus": "SFX",
                    "target_peak_db": -3.0 if role == "ui" else -1.5,
                    "fade_ms": 2,
                    "loop": False,
                }
            )

    sheet = {
        "pack": pack,
        "source_dir": str(source_dir.relative_to(ROOT)),
        "output_dir": output_dir,
        "buses": [
            {"name": "Music", "send": "Master", "volume_db": -6.0},
            {"name": "SFX", "send": "Master", "volume_db": -3.0},
            {"name": "VOX", "send": "Master", "volume_db": 0.0},
            {"name": "Ambience", "send": "Master", "volume_db": -9.0},
        ],
        "cues": cue_list,
    }
    return {"status": "ok", "llm_used": llm_used, "cue_sheet": sheet}


def synthesize_sfx(arguments: dict) -> dict:
    spec = arguments["spec"]
    kind = str(spec.get("kind", "noise_burst"))
    duration = float(spec.get("duration", 0.25))
    rate = int(spec.get("sample_rate", 44100))
    out_path = ROOT / str(arguments["out_path"])
    rng = np.random.default_rng(int(spec.get("seed", 0)))
    t = np.linspace(0.0, duration, int(rate * duration), endpoint=False)

    if kind == "noise_burst":
        decay = float(spec.get("decay", 18.0))
        audio = rng.uniform(-1.0, 1.0, len(t)) * np.exp(-t * decay)
    elif kind == "sweep":
        f0, f1 = float(spec.get("f0", 900.0)), float(spec.get("f1", 90.0))
        audio = np.sin(2 * np.pi * (f0 + (f1 - f0) * t / duration) * t) * np.exp(-t * 6.0)
    elif kind == "impact":
        audio = rng.uniform(-1.0, 1.0, len(t)) * np.exp(-t * 30.0) + np.sin(2 * np.pi * 90 * t) * np.exp(-t * 12.0)
    elif kind == "hum":
        audio = np.sin(2 * np.pi * float(spec.get("freq", 60.0)) * t) * 0.6
    else:
        raise ValueError(f"Unknown SFX kind: {kind}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    _write_wav(out_path, np.clip(audio, -1.0, 1.0), rate)
    return {"status": "ok", "out_path": _display_path(out_path), "duration": duration, "kind": kind}


def master_audio(arguments: dict) -> dict:
    source = ROOT / str(arguments["source_path"])
    out_path = ROOT / str(arguments["out_path"])
    target_peak_db = float(arguments.get("target_peak_db", -1.5))
    soft_clip = bool(arguments.get("soft_clip", True))
    fade_ms = int(arguments.get("fade_ms", 3))
    target_lufs = arguments.get("target_lufs_db")

    audio, rate, channels = _read_wav(source)
    lufs_before = None
    if target_lufs is not None:
        weighted = _k_weight(audio if audio.ndim == 1 else audio.mean(axis=1), rate)
        mean_sq = float(np.mean(np.square(weighted)))
        lufs_before = -0.691 + 10.0 * math.log10(max(mean_sq, 1e-12))
        audio = audio * _db_to_lin(float(target_lufs) - lufs_before)

    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    ceiling = _db_to_lin(target_peak_db)
    if peak > ceiling:
        audio = audio * (ceiling / peak)
    if soft_clip:
        audio = np.tanh(audio)
    if fade_ms > 0:
        frames = min(int(rate * fade_ms / 1000.0), max(1, len(audio) // 2))
        ramp = np.linspace(0.0, 1.0, frames, dtype=np.float32)
        if audio.ndim == 1:
            audio[:frames] *= ramp
            audio[-frames:] *= ramp[::-1]
        else:
            audio[:frames, :] *= ramp[:, None]
            audio[-frames:, :] *= ramp[::-1, None]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    _write_wav(out_path, audio, rate)
    lufs_after = None
    if target_lufs is not None:
        weighted = _k_weight(audio if audio.ndim == 1 else audio.mean(axis=1), rate)
        lufs_after = -0.691 + 10.0 * math.log10(max(float(np.mean(np.square(weighted))), 1e-12))
    final = float(np.max(np.abs(audio)))
    return {
        "status": "ok",
        "out_path": _display_path(out_path),
        "peak_db": round(_lin_to_db(final), 2),
        "rms_db": round(_lin_to_db(float(np.sqrt(np.mean(np.square(audio))))), 2),
        "lufs_before": round(lufs_before, 2) if lufs_before is not None else None,
        "target_lufs_db": float(target_lufs) if target_lufs is not None else None,
        "lufs_after": round(lufs_after, 2) if lufs_after is not None else None,
        "sample_rate": rate,
    }


def tts_synthesize(arguments: dict) -> dict:
    text = str(arguments["text"])
    out_path = ROOT / str(arguments["out_path"])
    voice = str(arguments.get("voice", "en_US-lessac-medium"))
    command_template = os.environ.get("TTS_COMMAND") or (
        "piper --model {voice} --output_file {out}"
    )
    if shutil.which("piper") is None and "TTS_COMMAND" not in os.environ:
        return {
            "status": "backend_unavailable",
            "reason": "piper not on PATH and TTS_COMMAND is not set",
            "text": text,
            "voice": voice,
        }
    rendered = command_template.format(voice=voice, out=str(out_path), text=text)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(rendered, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        return {"status": "error", "stderr": result.stderr[-500:]}
    return {"status": "ok", "out_path": _display_path(out_path)}


def pack_cues(arguments: dict) -> dict:
    cue_sheet = ROOT / str(arguments.get("cue_sheet", "audio/cue_sheet.json"))
    cmd = [sys.executable, str(ROOT / "tools/pack_audio_assets.py"), "--cue-sheet", str(cue_sheet)]
    if arguments.get("dry_run"):
        cmd.append("--dry-run")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
    return {
        "status": "ok" if result.returncode == 0 else "error",
        "returncode": result.returncode,
        "stdout": result.stdout[-2000:],
        "stderr": result.stderr[-1000:],
    }


def generate_sheet_image(arguments: dict) -> dict:
    backend_env = os.environ.get("IMAGE_BACKEND", "").strip().lower()
    if backend_env not in ("comfyui", "diffusers"):
        return {
            "status": "backend_unavailable",
            "reason": "IMAGE_BACKEND is not set to comfyui or diffusers",
            "hint": "Set IMAGE_BACKEND=comfyui (COMFYUI_URL/COMFYUI_CHECKPOINT) "
            "or IMAGE_BACKEND=diffusers (LOCAL_DIFFUSERS_MODEL)",
        }
    module_path = ROOT / "tools" / "local_image_backend.py"
    if not module_path.exists():
        return {"status": "error", "reason": f"Missing backend module: {module_path}"}
    spec = importlib.util.spec_from_file_location("local_image_backend", module_path)
    backend_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(backend_module)

    output_path = Path(str(arguments["output_path"]))
    if not output_path.is_absolute():
        output_path = ROOT / output_path
    backend = str(arguments.get("backend", backend_env))
    if backend == "auto":
        backend = backend_env
    return backend_module.generate_sheet_image(
        prompt=str(arguments["prompt"]),
        output_path=output_path,
        backend=backend,
        width=int(arguments.get("width", 1344)),
        height=int(arguments.get("height", 768)),
        steps=int(arguments.get("steps", 24)),
        cfg=float(arguments.get("cfg", 6.5)),
        seed=arguments.get("seed"),
        chroma_key=bool(arguments.get("chroma_key", True)),
    )


TOOLS: dict[str, dict] = {
    "list_backends": {
        "description": "Report which audio backends and executables are available.",
        "input_schema": {"type": "object", "properties": {}},
        "handler": list_backends,
    },
    "generate_cue_sheet": {
        "description": "Generate a cue sheet from a brief via Ollama, with a deterministic offline fallback.",
        "input_schema": {
            "type": "object",
            "required": ["brief"],
            "properties": {
                "brief": {"type": "string"},
                "pack": {"type": "string"},
                "source_dir": {"type": "string"},
                "output_dir": {"type": "string"},
                "use_llm": {"type": "boolean"},
                "model": {"type": "string"},
            },
        },
        "handler": generate_cue_sheet,
    },
    "synthesize_sfx": {
        "description": "Deterministically synthesize a procedural SFX WAV.",
        "input_schema": {
            "type": "object",
            "required": ["spec", "out_path"],
            "properties": {
                "spec": {
                    "type": "object",
                    "properties": {
                        "kind": {"type": "string", "enum": ["noise_burst", "sweep", "impact", "hum"]},
                        "duration": {"type": "number"},
                        "sample_rate": {"type": "integer"},
                        "seed": {"type": "integer"},
                        "decay": {"type": "number"},
                        "f0": {"type": "number"},
                        "f1": {"type": "number"},
                        "freq": {"type": "number"},
                    },
                },
                "out_path": {"type": "string"},
            },
        },
        "handler": synthesize_sfx,
    },
    "master_audio": {
        "description": "Normalize, soft-limit and fade a WAV deterministically.",
        "input_schema": {
            "type": "object",
            "required": ["source_path", "out_path"],
            "properties": {
                "source_path": {"type": "string"},
                "out_path": {"type": "string"},
                "target_peak_db": {"type": "number"},
                "target_lufs_db": {"type": "number"},
                "soft_clip": {"type": "boolean"},
                "fade_ms": {"type": "integer"},
            },
        },
        "handler": master_audio,
    },
    "tts_synthesize": {
        "description": "Synthesize speech via piper or TTS_COMMAND; reports backend_unavailable otherwise.",
        "input_schema": {
            "type": "object",
            "required": ["text", "out_path"],
            "properties": {
                "text": {"type": "string"},
                "out_path": {"type": "string"},
                "voice": {"type": "string"},
            },
        },
        "handler": tts_synthesize,
    },
    "pack_cues": {
        "description": "Run the deterministic audio packer on a cue sheet.",
        "input_schema": {
            "type": "object",
            "properties": {
                "cue_sheet": {"type": "string"},
                "dry_run": {"type": "boolean"},
            },
        },
        "handler": pack_cues,
    },
    "generate_sheet_image": {
        "description": "Generate an image sheet via local ComfyUI/Diffusers when IMAGE_BACKEND is configured.",
        "input_schema": {
            "type": "object",
            "required": ["prompt", "output_path"],
            "properties": {
                "prompt": {"type": "string"},
                "output_path": {"type": "string"},
                "backend": {"type": "string", "enum": ["auto", "comfyui", "diffusers"]},
                "width": {"type": "integer"},
                "height": {"type": "integer"},
                "steps": {"type": "integer"},
                "cfg": {"type": "number"},
                "seed": {"type": "integer"},
                "chroma_key": {"type": "boolean"},
            },
        },
        "handler": generate_sheet_image,
    },
}


def call_tool(name: str, arguments: dict | None = None) -> dict:
    if name not in TOOLS:
        raise KeyError(f"Unknown tool: {name}")
    handler: Callable[[dict], dict] = TOOLS[name]["handler"]
    return handler(arguments or {})


def main() -> int:
    parser = argparse.ArgumentParser(description="Studio audio tool surface.")
    parser.add_argument("--list", action="store_true", help="Print tool definitions as JSON.")
    parser.add_argument("--call", metavar="NAME")
    parser.add_argument("--args", default="{}", help="JSON arguments for --call")
    args = parser.parse_args()

    if args.list:
        print(
            json.dumps(
                [{"name": k, "description": v["description"], "inputSchema": v["input_schema"]} for k, v in TOOLS.items()],
                indent=2,
            )
        )
        return 0

    if not args.call:
        parser.error("Provide --list or --call NAME")
        return 2

    try:
        result = call_tool(args.call, json.loads(args.args))
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, indent=2))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
