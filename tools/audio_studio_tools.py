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
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")


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


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _db_to_lin(db: float) -> float:
    return 10.0 ** (db / 20.0)


def _lin_to_db(value: float) -> float:
    return 20.0 * math.log10(max(value, 1e-9))


def _ollama_generate(model: str, prompt: str) -> str | None:
    payload = json.dumps({"model": model, "prompt": prompt, "format": "json", "stream": False}).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_HOST}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
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
    model = str(arguments.get("model", "llama3.2"))

    cue_list = None
    llm_used = False
    if use_llm:
        prompt = (
            "Return ONLY JSON: {\"cues\":[{\"id\":str,\"source\":str,\"role\":"
            "\"sfx\"|\"ui\"|\"vox\"|\"bgm\"|\"ambience\",\"bus\":"
            "\"SFX\"|\"VOX\"|\"Music\"|\"Ambience\",\"target_peak_db\":number,"
            "\"fade_ms\":number,\"loop\":bool}]}. "
            f"Brief: {brief}. Source files: "
            + ", ".join(p.name for p in sorted(source_dir.glob("*.wav")))
        )
        raw = _ollama_generate(model, prompt)
        if raw:
            try:
                cue_list = json.loads(raw).get("cues")
                llm_used = True
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

    audio, rate, channels = _read_wav(source)
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak > 0.0:
        audio = audio * (_db_to_lin(target_peak_db) / peak)
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
    final = float(np.max(np.abs(audio)))
    return {
        "status": "ok",
        "out_path": _display_path(out_path),
        "peak_db": round(_lin_to_db(final), 2),
        "rms_db": round(_lin_to_db(float(np.sqrt(np.mean(np.square(audio))))), 2),
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
