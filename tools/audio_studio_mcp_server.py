# As Above, So Below. As Within, So Without.
# The Future Dictates the Past and the Past is Always Present.

"""Minimal stdio MCP server exposing the audio studio tool registry.

Implements the JSON-RPC 2.0 subset the Model Context Protocol needs:
initialize, tools/list, tools/call, ping. No third-party dependency, so it
can run anywhere Python 3.10+ runs. Add it to your studio's MCP client as:

    {"command": "python", "args": ["C:/godot4-asset-vault/tools/audio_studio_mcp_server.py"]}
"""

from __future__ import annotations

import argparse
import json
import sys

from audio_studio_tools import TOOLS, call_tool

PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "godot4-asset-vault-audio-studio"
SERVER_VERSION = "1.0.0"


def _tool_listings() -> list[dict]:
    return [
        {
            "name": name,
            "description": spec["description"],
            "inputSchema": spec["input_schema"],
        }
        for name, spec in TOOLS.items()
    ]


def handle_message(message: dict) -> dict | None:
    request_id = message.get("id")
    method = message.get("method")

    if method is None or str(method).startswith("notifications/"):
        return None

    if method == "initialize":
        result = {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
        }
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": _tool_listings()}
    elif method == "tools/call":
        params = message.get("params") or {}
        name = params.get("name")
        arguments = params.get("arguments") or {}
        try:
            data = call_tool(str(name), arguments)
            is_error = data.get("status") == "error"
            result = {
                "content": [{"type": "text", "text": json.dumps(data, indent=2)}],
                "isError": is_error,
            }
        except Exception as exc:
            result = {
                "content": [{"type": "text", "text": json.dumps({"status": "error", "error": str(exc)})}],
                "isError": True,
            }
    else:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        }

    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def self_test() -> int:
    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": "ping"},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/list"},
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "list_backends", "arguments": {}},
        },
        {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "synthesize_sfx",
                "arguments": {
                    "spec": {"kind": "sweep", "duration": 0.2, "seed": 3},
                    "out_path": "C:/Users/612co/AppData/Local/Temp/opencode/studio_test/mcp_sweep.wav",
                },
            },
        },
        {"jsonrpc": "2.0", "id": 6, "method": "tools/call", "params": {"name": "no_such_tool", "arguments": {}}},
    ]
    for req in requests:
        response = handle_message(req)
        print(json.dumps(response))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="stdio MCP server for the audio studio tool registry.")
    parser.add_argument("--self-test", action="store_true", help="Run an in-process protocol smoke test.")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except ValueError:
            response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
        else:
            response = handle_message(message)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
