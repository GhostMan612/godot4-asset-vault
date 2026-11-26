#!/usr/bin/env python3
# ============================================================
# As Above, So Below. As Within, So Without.
# The Future Dictates the Past and the Past is Always Present.
# ============================================================
import hashlib
import json
import runpy
import subprocess
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent


def digest(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def main() -> None:
    for tool in ("tools/bootstrap_vault.py", "tools/build_theme_packs.py"):
        p = ROOT / tool
        if p.exists():
            runpy.run_path(str(p), run_name="__main__")
    godot = "C:\\Godot\\Godot_v4.0-stable_win64_console.exe"
    if Path(godot).exists():
        for _ in range(2):
            subprocess.run([godot, "--headless", "--path", str(ROOT), "--editor", "--quit"], capture_output=True)
    entries = []
    for base in (ROOT / "assets", ROOT / "themes"):
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix.lower() in {".import", ".json", ".gd"}:
                continue
            dims, alpha = None, False
            if path.suffix.lower() in {".png", ".svg"}:
                try:
                    im = Image.open(path)
                    dims = list(im.size)
                    alpha = "A" in im.getbands()
                except Exception:
                    pass
            entries.append({
                "path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size,
                "dimensions": dims, "rgba": alpha, "sha256": digest(path), "provenance": "ORIGINAL_PROCEDURAL",
            })
    (ROOT / "ASSET_MANIFEST.json").write_text(json.dumps({"assets": entries}, indent=2) + "\n", encoding="utf-8")
    print(f"manifest written: {len(entries)} assets")


if __name__ == "__main__":
    main()
