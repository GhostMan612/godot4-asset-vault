# As Above, So Below. As Within, So Without.
# The Future Dictates the Past and the Past is Always Present.

from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
import tempfile
import urllib.parse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from studio_service.android_apk_bundle import (
    BUNDLES_DIR,
    generate_android_apk_package,
    generate_background_asset,
    slugify,
    synthesize_bgm_loop,
    synthesize_ui_sfx,
)


class VaultAPIHandler(BaseHTTPRequestHandler):
    def _send_json(self, code: int, payload: dict) -> None:
        raw = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _send_file(self, file_path: Path, content_type: str) -> None:
        raw = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Disposition", f'attachment; filename="{file_path.name}"')
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/health":
            self._send_json(200, {"status": "ok", "service": "godot4-asset-vault-foundry"})
            return
        if parsed.path.startswith("/api/v1/bundles/"):
            fname = Path(parsed.path).name
            target = (BUNDLES_DIR / fname).resolve()
            if target.is_relative_to(BUNDLES_DIR.resolve()) and target.is_file():
                ctype = "application/zip" if target.suffix == ".zip" else "application/octet-stream"
                self._send_file(target, ctype)
                return
            self._send_json(404, {"error": "bundle_not_found"})
            return
        self._send_json(404, {"error": "not_found"})

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        try:
            body = self._read_json_body()
            if parsed.path == "/api/v1/android/apk-bundle":
                result = generate_android_apk_package(
                    app_name=body.get("app_name", "SovereignApp"),
                    package_id=body.get("package_id", "com.sovereign.app"),
                    genre=body.get("genre", "tactical"),
                    brief=body.get("brief", ""),
                )
                result["download_url"] = f"/api/v1/bundles/{result['zip_name']}"
                if qs.get("download", ["false"])[0].lower() == "true":
                    self._send_file(Path(result["zip_path"]), "application/zip")
                    return
                self._send_json(200, result)
                return

            if parsed.path == "/api/v1/assets/background":
                slug = slugify(body.get("name", "custom_bg"))
                out_path = BUNDLES_DIR / f"{slug}.png"
                res = generate_background_asset(
                    app_name=body.get("app_name", "SovereignApp"),
                    theme_prompt=body.get("prompt", "dark gothic archive"),
                    width=int(body.get("width", 1080)),
                    height=int(body.get("height", 1920)),
                    output_path=out_path,
                )
                res["download_url"] = f"/api/v1/bundles/{out_path.name}"
                self._send_json(200, res)
                return

            if parsed.path == "/api/v1/assets/sfx":
                kind = body.get("kind", "tap")
                out_path = BUNDLES_DIR / f"sfx_{slugify(kind)}.wav"
                res = synthesize_ui_sfx(kind, out_path)
                res["download_url"] = f"/api/v1/bundles/{out_path.name}"
                self._send_json(200, res)
                return

            if parsed.path == "/api/v1/assets/bgm":
                track = body.get("track_type", "title_theme")
                dur = float(body.get("duration_s", 8.0))
                out_path = BUNDLES_DIR / f"bgm_{slugify(track)}.wav"
                res = synthesize_bgm_loop(track, out_path, duration_s=dur)
                res["download_url"] = f"/api/v1/bundles/{out_path.name}"
                self._send_json(200, res)
                return

            self._send_json(404, {"error": "not_found"})
        except Exception as exc:
            self._send_json(500, {"error": str(exc)})


def run_self_test() -> dict:
    with tempfile.TemporaryDirectory(prefix="vault_rest_selftest_") as tmp:
        res = generate_android_apk_package(
            app_name="SelfTestApp",
            package_id="com.sovereign.selftest",
            genre="gothic tactical",
            brief="Self-test Android Play Store bundle",
            output_dir=Path(tmp),
        )
        assert res["play_store_compliant"] is True
        assert res["file_count"] >= 35
        return {"status": "ok", "self_test": "passed", "bundle_files": res["file_count"], "size_mb": res["size_mb"]}


def main() -> int:
    parser = argparse.ArgumentParser(description="Godot4 Asset Vault REST Foundry Server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        print(json.dumps(run_self_test(), indent=2))
        return 0

    BUNDLES_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((args.host, args.port), VaultAPIHandler)
    print(f"Vault Foundry REST API listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
