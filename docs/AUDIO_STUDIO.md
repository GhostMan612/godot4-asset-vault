# Audio Studio Tool Surface

The vault exposes its audio pipeline as plain Python callables with JSON
Schemas, plus a stdio MCP server. Deterministic DSP works offline; generative
tools connect to local backends when available.

## Deterministic tools (no backend needed)

| Tool | Purpose |
|---|---|
| `list_backends` | Report ffmpeg / sox / piper / Ollama availability |
| `synthesize_sfx` | Seeded procedural WAVs: `noise_burst`, `sweep`, `impact`, `hum` |
| `master_audio` | Optional K-weighted LUFS targeting, peak ceiling, soft limiting, fades |
| `pack_cues` | Run `tools/pack_audio_assets.py` on a cue sheet |

## AI-assisted tools

| Tool | Backend |
|---|---|
| `generate_cue_sheet` | Ollama `/api/generate`; deterministic fallback when unreachable |
| `tts_synthesize` | `piper` on PATH, or a command set in `TTS_COMMAND` |

## Ollama

`OLLAMA_HOST` is normalized automatically, with or without a scheme. Example:

```
OLLAMA_HOST=http://127.0.0.1:11450
```

The default model is `qwen2.5:3b`. CPU inference needs a generous timeout
(180 s in the tool). LLM cue output is sanitized: bus aliases are mapped to
`SFX`/`VOX`/`Music`/`Ambience`, peak is clamped to `-12..-1 dBFS`, fades to
`0..20 ms`, source filenames must exist, and IDs are slugified.

## MCP client configuration

```json
{
  "mcpServers": {
    "vault-audio": {
      "command": "python",
      "args": ["C:/godot4-asset-vault/tools/audio_studio_mcp_server.py"]
    }
  }
}
```

The server implements `initialize`, `tools/list`, `tools/call`, and `ping`
over newline-delimited JSON-RPC 2.0 on stdio. Verify locally with:

```
python tools/audio_studio_mcp_server.py --self-test
```

## Vault integration

Cue sheets live in `audio/cue_sheet.json`. Packed output lands in the target
game's `audio/packed/` folder with:

- normalized WAV clips
- `audio_bus_layout.tres` (Music / SFX / VOX / Ambience over Master)
- `audio_cue_registry.gd` with `has_cue()` and `stream_for()`
- `audio_manifest.json` with deterministic hashes

Raw stems and generated masters should stay out of Git; only deliverables and
the lightweight manifest are committed.
