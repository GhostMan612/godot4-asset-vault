# As Above, So Below. As Within, So Without.
# The Future Dictates the Past and the Past is Always Present.

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import urllib.error
import urllib.request


@dataclass(frozen=True)
class FoundryConfig:
    venv_hub_dir: str = os.environ.get("VENV_HUB_DIR", r"C:\venv-hub")
    ollama_url: str = os.environ.get("LOCAL_LLM_URL", "http://127.0.0.1:11450")
    ollama_models_dir: str = os.environ.get("OLLAMA_MODELS", r"D:\ollama\models")
    ollama_model: str = os.environ.get("LOCAL_LLM_MODEL", "llama3.1:8b")
    tcs_repo_dir: str = os.environ.get("TCS_REPO_DIR", r"C:\Toxic Creationz Studio")
    tcs_api_url: str = os.environ.get("TCS_API_URL", "http://127.0.0.1:8000")
    comfyui_url: str = os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188")
    image_backend: str = os.environ.get("IMAGE_BACKEND", "auto")
    vault_api_host: str = os.environ.get("VAULT_API_HOST", "127.0.0.1")
    vault_api_port: int = int(os.environ.get("VAULT_API_PORT", "8787"))


def _probe_http(url: str, timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return 200 <= resp.status < 400
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def check_environment(cfg: FoundryConfig | None = None) -> dict:
    c = cfg or FoundryConfig()
    return {
        "config": asdict(c),
        "paths": {
            "venv_hub_exists": Path(c.venv_hub_dir).exists(),
            "ollama_models_exists": Path(c.ollama_models_dir).exists(),
            "tcs_repo_exists": Path(c.tcs_repo_dir).exists(),
        },
        "services": {
            "ollama_11450_online": _probe_http(f"{c.ollama_url.rstrip('/')}/api/tags"),
            "tcs_api_online": _probe_http(f"{c.tcs_api_url.rstrip('/')}/health"),
            "comfyui_online": _probe_http(f"{c.comfyui_url.rstrip('/')}/system_stats"),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect Asset Foundry local config and live services.")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        print(json.dumps(check_environment(), indent=2))
        return 0
    print(json.dumps(asdict(FoundryConfig()), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
