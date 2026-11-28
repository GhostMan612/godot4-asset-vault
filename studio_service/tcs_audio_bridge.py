# As Above, So Below. As Within, So Without.
# The Future Dictates the Past and the Past is Always Present.

from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from studio_service.foundry_config import FoundryConfig

AUDIO_TOOL_CANDIDATES = (
    "generate_audio",
    "render_audio",
    "generate_bgm",
    "generate_sfx",
    "synthesize_audio",
)


def _json_rpc_http(url: str, method: str, params: dict | None = None, req_id: int = 1, timeout: int = 15) -> dict:
    payload = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params or {}}
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _json_rpc_stdio(cmd: list[str], cwd: str, method: str, params: dict | None = None, timeout: int = 20) -> dict:
    init_req = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "godot4-asset-vault", "version": "1.0.0"},
            },
        }
    )
    call_req = json.dumps({"jsonrpc": "2.0", "id": 2, "method": method, "params": params or {}})
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        input=f"{init_req}\n{call_req}\n",
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    for line in reversed(proc.stdout.splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        parsed = json.loads(line)
        if parsed.get("id") == 2:
            return parsed
    raise RuntimeError("No matching JSON-RPC response from TCS MCP stdio server")


def _extract_audio_payload(payload: dict, output_path: Path) -> bool:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    for key in ("output_path", "file_path", "wav_path", "path"):
        val = payload.get(key)
        if isinstance(val, str) and Path(val).is_file():
            shutil.copy2(Path(val), output_path)
            return True
    for key in ("audio_base64", "wav_base64", "data_base64"):
        val = payload.get(key)
        if isinstance(val, str) and val:
            output_path.write_bytes(base64.b64decode(val))
            return True
    return False


def _unpack_mcp_result(rpc_response: dict, output_path: Path) -> bool:
    result = rpc_response.get("result")
    if not isinstance(result, dict):
        return False
    if _extract_audio_payload(result, output_path):
        return True
    for item in result.get("content", []):
        if not isinstance(item, dict):
            continue
        if item.get("type") == "audio" and isinstance(item.get("data"), str):
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(base64.b64decode(item["data"]))
            return True
        text = item.get("text")
        if isinstance(text, str) and text.strip().startswith("{"):
            try:
                if _extract_audio_payload(json.loads(text), output_path):
                    return True
            except json.JSONDecodeError:
                pass
    return False


def _discover_mcp_tool(mcp_url: str, preferred_tool: str) -> str:
    if preferred_tool:
        return preferred_tool
    try:
        listed = _json_rpc_http(mcp_url, "tools/list", {}, req_id=1, timeout=4)
        names = [t.get("name", "") for t in listed.get("result", {}).get("tools", []) if isinstance(t, dict)]
        for candidate in AUDIO_TOOL_CANDIDATES:
            if candidate in names:
                return candidate
        if names:
            return names[0]
    except Exception:
        pass
    return AUDIO_TOOL_CANDIDATES[0]


def try_tcs_mcp_audio(
    prompt: str,
    category: str,
    duration_s: float,
    output_path: Path,
    target_lufs: float = -16.0,
    cfg: FoundryConfig | None = None,
) -> dict | None:
    c = cfg or FoundryConfig()
    mcp_url = os.environ.get("TCS_MCP_URL", f"{c.tcs_api_url.rstrip('/')}/mcp").strip()
    mcp_cmd = os.environ.get("TCS_MCP_CMD", "").strip()
    preferred_tool = os.environ.get("TCS_MCP_TOOL", "").strip()

    tool_args = {
        "prompt": prompt,
        "category": category,
        "duration_s": duration_s,
        "format": "wav",
        "target_lufs": target_lufs,
        "output_path": str(output_path),
    }

    if mcp_url:
        try:
            tool_name = _discover_mcp_tool(mcp_url, preferred_tool)
            rpc = _json_rpc_http(
                mcp_url,
                "tools/call",
                {"name": tool_name, "arguments": tool_args},
                req_id=2,
                timeout=20,
            )
            if _unpack_mcp_result(rpc, output_path):
                return {
                    "engine": f"tcs_mcp_http:{tool_name}",
                    "path": str(output_path),
                    "duration_s": duration_s,
                    "target_lufs": target_lufs,
                }
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError, ValueError):
            pass

    if mcp_cmd and Path(c.tcs_repo_dir).exists():
        try:
            tool_name = preferred_tool or AUDIO_TOOL_CANDIDATES[0]
            rpc = _json_rpc_stdio(
                mcp_cmd.split(),
                cwd=c.tcs_repo_dir,
                method="tools/call",
                params={"name": tool_name, "arguments": tool_args},
                timeout=25,
            )
            if _unpack_mcp_result(rpc, output_path):
                return {
                    "engine": f"tcs_mcp_stdio:{tool_name}",
                    "path": str(output_path),
                    "duration_s": duration_s,
                    "target_lufs": target_lufs,
                }
        except Exception:
            pass

    return None


def try_tcs_rest_audio(
    prompt: str,
    category: str,
    duration_s: float,
    output_path: Path,
    target_lufs: float = -16.0,
    cfg: FoundryConfig | None = None,
) -> dict | None:
    c = cfg or FoundryConfig()
    endpoint = os.environ.get("TCS_RENDER_ENDPOINT", "/api/v1/audio/generate")
    url = f"{c.tcs_api_url.rstrip('/')}{endpoint}"
    payload = {
        "prompt": prompt,
        "category": category,
        "duration_s": duration_s,
        "format": "wav",
        "target_lufs": target_lufs,
    }
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            ctype = resp.headers.get("Content-Type", "")
            raw = resp.read()
            if "audio/" in ctype or raw[:4] == b"RIFF":
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(raw)
                return {
                    "engine": "tcs_rest_binary",
                    "path": str(output_path),
                    "duration_s": duration_s,
                    "target_lufs": target_lufs,
                }
            if "application/json" in ctype:
                if _extract_audio_payload(json.loads(raw.decode("utf-8")), output_path):
                    return {
                        "engine": "tcs_rest_json",
                        "path": str(output_path),
                        "duration_s": duration_s,
                        "target_lufs": target_lufs,
                    }
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError, ValueError):
        return None
    return None


def request_tcs_audio(
    prompt: str,
    category: str,
    duration_s: float,
    output_path: Path,
    target_lufs: float = -16.0,
    cfg: FoundryConfig | None = None,
) -> dict | None:
    mcp_res = try_tcs_mcp_audio(prompt, category, duration_s, output_path, target_lufs=target_lufs, cfg=cfg)
    if mcp_res is not None:
        return mcp_res
    return try_tcs_rest_audio(prompt, category, duration_s, output_path, target_lufs=target_lufs, cfg=cfg)


def probe_tcs(cfg: FoundryConfig | None = None) -> dict:
    c = cfg or FoundryConfig()
    mcp_url = os.environ.get("TCS_MCP_URL", f"{c.tcs_api_url.rstrip('/')}/mcp").strip()
    mcp_tools: list[str] = []
    mcp_online = False
    try:
        listed = _json_rpc_http(mcp_url, "tools/list", {}, req_id=1, timeout=3)
        mcp_tools = [t.get("name", "") for t in listed.get("result", {}).get("tools", []) if isinstance(t, dict)]
        mcp_online = True
    except Exception:
        pass

    rest_online = False
    try:
        with urllib.request.urlopen(f"{c.tcs_api_url.rstrip('/')}/health", timeout=3) as resp:
            rest_online = 200 <= resp.status < 400
    except Exception:
        pass

    return {
        "tcs_repo_dir": c.tcs_repo_dir,
        "tcs_repo_exists": Path(c.tcs_repo_dir).exists(),
        "tcs_api_url": c.tcs_api_url,
        "tcs_rest_online": rest_online,
        "tcs_mcp_url": mcp_url,
        "tcs_mcp_online": mcp_online,
        "tcs_mcp_tools": mcp_tools,
    }


def run_self_test() -> dict:
    with tempfile.TemporaryDirectory(prefix="tcs_bridge_test_") as tmp:
        out_wav = Path(tmp) / "test.wav"
        fake_b64 = base64.b64encode(b"RIFF\x24\x00\x00\x00WAVE").decode("ascii")
        rpc = {"jsonrpc": "2.0", "id": 2, "result": {"content": [{"type": "text", "text": json.dumps({"wav_base64": fake_b64})}]}}
        assert _unpack_mcp_result(rpc, out_wav) is True
        assert out_wav.read_bytes().startswith(b"RIFF")
    return {
        "status": "ok",
        "self_test": "passed",
        "transports": ["tcs_mcp_http", "tcs_mcp_stdio", "tcs_rest"],
        "env_vars": ["TCS_API_URL", "TCS_MCP_URL", "TCS_MCP_CMD", "TCS_MCP_TOOL", "TCS_RENDER_ENDPOINT"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Toxic Creationz Studio MCP + REST audio bridge.")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--probe", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps(run_self_test(), indent=2))
        return 0
    if args.probe:
        print(json.dumps(probe_tcs(), indent=2))
        return 0
    print(json.dumps(probe_tcs(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
