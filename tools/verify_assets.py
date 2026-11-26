#!/usr/bin/env python3
# ============================================================
# As Above, So Below. As Within, So Without.
# The Future Dictates the Past and the Past is Always Present.
# ============================================================
import argparse
import re
import struct
import subprocess
import sys
import zlib
from pathlib import Path

ASSET_SUFFIXES = {".png", ".svg", ".wav"}
REFERENCE_FILES = [
    "scripts/tileset_theme_registry.gd", "scripts/ui/icon_registry.gd",
    "scripts/audio/tactical_audio.gd", "scripts/view3d/world_view_3d.gd",
]


def tracked(root: Path, rel: Path) -> bool:
    repo = root
    parts = rel.parts
    if len(parts) > 2 and parts[0] == "addons" and parts[1] == "godot4-asset-vault":
        repo = root / "addons" / "godot4-asset-vault"
        rel = Path(*parts[2:])
    result = subprocess.run(["git", "-C", str(repo), "ls-files", "--error-unmatch", rel.as_posix()], capture_output=True)
    return result.returncode == 0


def png_alpha(path: Path) -> tuple:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return (False, 255)
    pos, ihdr, idat = 8, None, bytearray()
    while pos + 8 <= len(data):
        size = struct.unpack(">I", data[pos:pos + 4])[0]
        kind = data[pos + 4:pos + 8]
        chunk = data[pos + 8:pos + 8 + size]
        if kind == b"IHDR":
            ihdr = struct.unpack(">IIBBBBB", chunk)
        elif kind == b"IDAT":
            idat.extend(chunk)
        pos += 12 + size
    if ihdr is None:
        return (False, 255)
    width, height, depth, color, _, _, interlace = ihdr
    if depth != 8 or color != 6 or interlace != 0:
        return (False, 255)
    raw = zlib.decompress(bytes(idat))
    return (True, raw[4])


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
                rgba, corner_alpha = png_alpha(path)
                if not rgba:
                    print(f"NOT RGBA {path.relative_to(root)}")
                    failures += 1
                elif corner_alpha != 0:
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


