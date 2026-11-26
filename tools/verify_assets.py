#!/usr/bin/env python3
# ============================================================
# As Above, So Below. As Within, So Without.
# The Future Dictates the Past and the Past is Always Present.
# ============================================================
import argparse
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image

ASSET_SUFFIXES = {".png", ".svg", ".wav"}
REFERENCE_FILES = [
    "scripts/tileset_theme_registry.gd", "scripts/ui/icon_registry.gd",
    "scripts/audio/tactical_audio.gd", "scripts/view3d/world_view_3d.gd",
]


def tracked(root: Path, rel: Path) -> bool:
    result = subprocess.run(["git", "-C", str(root), "ls-files", "--error-unmatch", rel.as_posix()], capture_output=True)
    return result.returncode == 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    ap.add_argument("--game", action="store_true")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    failures = 0
    search_roots = [root / p for p in ("assets", "themes") if (root / p).exists()]
    sub = root / "addons" / "godot4-asset-vault"
    if sub.exists():
        search_roots += [sub / p for p in ("assets", "themes") if (sub / p).exists()]
    for base in search_roots:
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in ASSET_SUFFIXES:
                continue
            imp = Path(str(path) + ".import")
            if not imp.exists():
                print(f"MISSING IMPORT {path.relative_to(root)}")
                failures += 1
            elif not tracked(root, path.relative_to(root)) or not tracked(root, imp.relative_to(root)):
                print(f"UNTRACKED {path.relative_to(root)}")
                failures += 1
    for base in search_roots:
        for path in base.rglob("*.png"):
            if "sprites" not in path.parts:
                continue
            try:
                im = Image.open(path)
                if im.mode != "RGBA":
                    print(f"NOT RGBA {path.relative_to(root)}")
                    failures += 1
                else:
                    alpha = im.getchannel("A")
                    if min(alpha.getpixel((0, 0)), alpha.getpixel((im.width - 1, 0))) != 0:
                        print(f"OPAQUE EDGE {path.relative_to(root)}")
                        failures += 1
            except Exception as exc:
                print(f"BAD IMAGE {path.relative_to(root)} {exc}")
                failures += 1
    if args.game:
        pattern = re.compile(r'res://(assets|addons/godot4-asset-vault)/[A-Za-z0-9_./-]+')
        for rel in REFERENCE_FILES:
            f = root / rel
            if not f.exists():
                continue
            for match in pattern.findall(f.read_text(encoding="utf-8")):
                target = root / match.replace("res://", "")
                if not target.exists():
                    print(f"MISSING REFERENCE {match} in {rel}")
                    failures += 1
    if not (root / "PROVENANCE.md").exists() and not (root / "THIRD_PARTY_LICENSES.md").exists():
        print("MISSING PROVENANCE.md")
        failures += 1
    print(f"VERIFY_ASSETS {'PASS' if failures == 0 else 'FAIL'} failures={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
