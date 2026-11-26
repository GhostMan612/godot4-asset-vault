# As Above, So Below. As Within, So Without.
# The Future Dictates the Past and the Past is Always Present.

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_NEGATIVE = (
    "grid lines, text, watermark, labels, drop shadow, floor shadow, gradient background, "
    "blurry, anti-aliased halo, photorealistic background"
)

CHROMA_SUFFIX = (
    "Completely flat uniform solid magenta (#FF00FF) background with zero grid lines, "
    "zero text, zero labels, and zero floor shadows."
)


def build_comfyui_workflow(
    prompt: str,
    negative_prompt: str,
    width: int,
    height: int,
    steps: int,
    cfg: float,
    seed: int,
    checkpoint: str,
) -> dict:
    return {
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0],
            },
        },
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": checkpoint},
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": width, "height": height, "batch_size": 1},
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": prompt, "clip": ["4", 1]},
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": negative_prompt, "clip": ["4", 1]},
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "vault_sheet", "images": ["8", 0]},
        },
    }


def _http_json(url: str, payload: dict | None = None, timeout: int = 30) -> dict:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"} if data is not None else {}
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def generate_via_comfyui(
    prompt: str,
    negative_prompt: str,
    output_path: Path,
    width: int,
    height: int,
    steps: int,
    cfg: float,
    seed: int,
    comfy_url: str,
    checkpoint: str,
    poll_timeout_s: int = 300,
) -> dict:
    base = comfy_url.rstrip("/")
    workflow = build_comfyui_workflow(
        prompt=prompt,
        negative_prompt=negative_prompt,
        width=width,
        height=height,
        steps=steps,
        cfg=cfg,
        seed=seed,
        checkpoint=checkpoint,
    )
    queued = _http_json(f"{base}/prompt", {"prompt": workflow})
    prompt_id = queued["prompt_id"]

    deadline = time.monotonic() + poll_timeout_s
    image_meta = None
    while time.monotonic() < deadline:
        history = _http_json(f"{base}/history/{prompt_id}")
        if prompt_id in history:
            outputs = history[prompt_id].get("outputs", {})
            for node_out in outputs.values():
                images = node_out.get("images", [])
                if images:
                    image_meta = images[0]
                    break
            if image_meta is not None:
                break
        time.sleep(1.0)

    if image_meta is None:
        raise TimeoutError(f"ComfyUI job {prompt_id} did not produce an image within {poll_timeout_s}s")

    query = urllib.parse.urlencode(
        {
            "filename": image_meta["filename"],
            "subfolder": image_meta.get("subfolder", ""),
            "type": image_meta.get("type", "output"),
        }
    )
    with urllib.request.urlopen(f"{base}/view?{query}", timeout=60) as resp:
        raw_bytes = resp.read()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(raw_bytes)
    return {
        "status": "ok",
        "backend": "comfyui",
        "output_path": str(output_path),
        "seed": seed,
        "width": width,
        "height": height,
        "checkpoint": checkpoint,
    }


def generate_via_diffusers(
    prompt: str,
    negative_prompt: str,
    output_path: Path,
    width: int,
    height: int,
    steps: int,
    cfg: float,
    seed: int,
    model_id: str,
) -> dict:
    import torch
    from diffusers import AutoPipelineForText2Image

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32
    pipe = AutoPipelineForText2Image.from_pretrained(model_id, torch_dtype=dtype)
    pipe = pipe.to(device)
    generator = torch.Generator(device=device).manual_seed(seed)

    result = pipe(
        prompt=prompt,
        negative_prompt=negative_prompt,
        width=width,
        height=height,
        num_inference_steps=steps,
        guidance_scale=cfg,
        generator=generator,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.images[0].save(output_path)
    return {
        "status": "ok",
        "backend": "diffusers",
        "device": device,
        "model_id": model_id,
        "output_path": str(output_path),
        "seed": seed,
        "width": width,
        "height": height,
    }


def generate_sheet_image(
    prompt: str,
    output_path: Path,
    backend: str = "auto",
    width: int = 1344,
    height: int = 768,
    steps: int = 24,
    cfg: float = 6.5,
    seed: int | None = None,
    chroma_key: bool = True,
    negative_prompt: str = DEFAULT_NEGATIVE,
) -> dict:
    final_seed = seed if seed is not None else random.randint(1, 2_147_483_647)
    final_prompt = f"{prompt.strip()} {CHROMA_SUFFIX}" if chroma_key else prompt.strip()

    comfy_url = os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188")
    comfy_ckpt = os.environ.get("COMFYUI_CHECKPOINT", "sd_xl_base_1.0.safetensors")
    diffusers_model = os.environ.get("LOCAL_DIFFUSERS_MODEL", "stabilityai/sdxl-turbo")

    chosen = backend
    if chosen == "auto":
        try:
            _http_json(f"{comfy_url.rstrip('/')}/system_stats", timeout=2)
            chosen = "comfyui"
        except (urllib.error.URLError, TimeoutError, OSError):
            chosen = "diffusers"

    if chosen == "comfyui":
        return generate_via_comfyui(
            prompt=final_prompt,
            negative_prompt=negative_prompt,
            output_path=output_path,
            width=width,
            height=height,
            steps=steps,
            cfg=cfg,
            seed=final_seed,
            comfy_url=comfy_url,
            checkpoint=comfy_ckpt,
        )
    if chosen == "diffusers":
        return generate_via_diffusers(
            prompt=final_prompt,
            negative_prompt=negative_prompt,
            output_path=output_path,
            width=width,
            height=height,
            steps=steps,
            cfg=cfg,
            seed=final_seed,
            model_id=diffusers_model,
        )
    raise ValueError(f"Unsupported backend: {chosen}")


def run_self_test() -> dict:
    wf = build_comfyui_workflow(
        prompt="test sprite sheet",
        negative_prompt=DEFAULT_NEGATIVE,
        width=1344,
        height=768,
        steps=20,
        cfg=6.5,
        seed=42,
        checkpoint="sd_xl_base_1.0.safetensors",
    )
    assert wf["3"]["inputs"]["seed"] == 42
    assert wf["5"]["inputs"]["width"] == 1344
    return {
        "status": "ok",
        "self_test": "passed",
        "backends": ["comfyui", "diffusers"],
        "env_vars": ["COMFYUI_URL", "COMFYUI_CHECKPOINT", "LOCAL_DIFFUSERS_MODEL"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Offline ComfyUI/Diffusers image backend for godot4-asset-vault.")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--prompt", default="")
    parser.add_argument("--output", default="")
    parser.add_argument("--backend", choices=("auto", "comfyui", "diffusers"), default="auto")
    parser.add_argument("--width", type=int, default=1344)
    parser.add_argument("--height", type=int, default=768)
    parser.add_argument("--steps", type=int, default=24)
    parser.add_argument("--cfg", type=float, default=6.5)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--no-chroma-key", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.self_test:
        print(json.dumps(run_self_test(), indent=2))
        return 0
    if not args.prompt or not args.output:
        print("ERROR: --prompt and --output are required unless --self-test is set.", file=sys.stderr)
        return 2
    result = generate_sheet_image(
        prompt=args.prompt,
        output_path=Path(args.output),
        backend=args.backend,
        width=args.width,
        height=args.height,
        steps=args.steps,
        cfg=args.cfg,
        seed=args.seed,
        chroma_key=not args.no_chroma_key,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
