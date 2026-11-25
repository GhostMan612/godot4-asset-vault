# As Above, So Below. As Within, So Without.
# The Future Dictates the Past and the Past is Always Present.

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENDOR_DIR = ROOT / "vendor"


@dataclass
class MirrorSpec:
    name: str
    group: str
    url: str
    target_rel: str
    license_name: str
    notes: str
    sparse_paths: list[str] = field(default_factory=list)


SPECS: list[MirrorSpec] = [
    MirrorSpec(
        name="Google Fonts Tactical HUD Set",
        group="fonts",
        url="https://github.com/google/fonts.git",
        target_rel="vendor/fonts_tactical",
        license_name="SIL OFL 1.1",
        notes="Oxanium, Chakra Petch, Rajdhani, Barlow Condensed, B612 Mono, Share Tech Mono, Black Ops One.",
        sparse_paths=[
            "ofl/oxanium",
            "ofl/chakrapetch",
            "ofl/rajdhani",
            "ofl/barlowcondensed",
            "ofl/b612mono",
            "ofl/sharetechmono",
            "ofl/blackopsone",
        ],
    ),
    MirrorSpec(
        name="Free Firearm Sound Library",
        group="audio",
        url="https://github.com/buddingmonkey/FreeFirearmsSFXLibrary.git",
        target_rel="vendor/sfx_firearms",
        license_name="CC0-1.0",
        notes="Real firearm recordings (AK-47, AR-15, shotgun, pistol, dry fire, mag loading) in WAV.",
    ),
    MirrorSpec(
        name="Kenney Interface Sounds (WAV)",
        group="audio",
        url="https://github.com/Calinou/kenney-interface-sounds.git",
        target_rel="vendor/sfx_kenney_interface",
        license_name="CC0-1.0",
        notes="100 interface SFX losslessly converted to WAV for Godot 4.",
    ),
    MirrorSpec(
        name="Kenney UI Audio (WAV)",
        group="audio",
        url="https://github.com/Calinou/kenney-ui-audio.git",
        target_rel="vendor/sfx_kenney_ui",
        license_name="CC0-1.0",
        notes="50 UI click and switch SFX in WAV for Godot 4.",
    ),
    MirrorSpec(
        name="Tabler Icons",
        group="icons",
        url="https://github.com/tabler/tabler-icons.git",
        target_rel="vendor/icons_tabler",
        license_name="MIT",
        notes="6,500+ uniform-stroke 24x24 SVG HUD and app icons.",
        sparse_paths=["icons", "LICENSE"],
    ),
    MirrorSpec(
        name="Lucide Icons",
        group="icons",
        url="https://github.com/lucide-icons/lucide.git",
        target_rel="vendor/icons_lucide",
        license_name="ISC",
        notes="2,000+ minimalist SVG icons for HUD and companion apps.",
        sparse_paths=["icons", "LICENSE"],
    ),
    MirrorSpec(
        name="Superpowers Asset Packs",
        group="sprites",
        url="https://github.com/sparklinlabs/superpowers-asset-packs.git",
        target_rel="vendor/sprites_superpowers",
        license_name="CC0-1.0",
        notes="Top-down shooter and space shooter 2D sprite packs.",
        sparse_paths=["top-down-shooter", "space-shooter", "README.md"],
    ),
]


def run_cmd(cmd: list[str], cwd: Path | None = None, dry_run: bool = False) -> str:
    printable = " ".join(cmd)
    if dry_run:
        print(f"[dry-run] {printable}")
        return "dry-run"
    res = subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True, check=True)
    return res.stdout.strip()


def sync_repo(spec: MirrorSpec, dry_run: bool = False) -> dict:
    dest = ROOT / spec.target_rel
    if dest.exists() and not dry_run:
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    if spec.sparse_paths:
        run_cmd(["git", "clone", "--depth", "1", "--filter=blob:none", "--sparse", spec.url, str(dest)], dry_run=dry_run)
        run_cmd(["git", "-C", str(dest), "sparse-checkout", "set", *spec.sparse_paths], dry_run=dry_run)
    else:
        run_cmd(["git", "clone", "--depth", "1", spec.url, str(dest)], dry_run=dry_run)

    commit_sha = "dry-run"
    if not dry_run:
        commit_sha = run_cmd(["git", "-C", str(dest), "rev-parse", "--short", "HEAD"])
        git_dir = dest / ".git"
        if git_dir.exists():
            shutil.rmtree(git_dir)

    return {
        "name": spec.name,
        "group": spec.group,
        "url": spec.url,
        "path": spec.target_rel,
        "license": spec.license_name,
        "commit": commit_sha,
        "notes": spec.notes,
    }


def run_plinkfx(dry_run: bool = False) -> dict | None:
    out_dir = ROOT / "vendor/sfx_plinkfx"
    if shutil.which("npx") is None and not dry_run:
        print("Skipping plinkfx: npx not found on PATH.")
        return None
    run_cmd(["npx", "--yes", "plinkfx", "export", "--out", str(out_dir), "--format", "wav"], dry_run=dry_run)
    return {
        "name": "plinkfx Procedural Tactical SFX",
        "group": "plinkfx",
        "url": "https://github.com/maximilianfeix/plinkfx",
        "path": "vendor/sfx_plinkfx",
        "license": "CC0-1.0 (audio) / MIT (code)",
        "commit": "npx-latest",
        "notes": "Deterministic BS.1770 loudness-matched WAV SFX generated via plinkfx CLI.",
    }


def write_licenses_and_manifest(records: list[dict], dry_run: bool = False) -> None:
    lines = [
        "# Third-Party Asset Licenses",
        "",
        f"Generated: `{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}` by `tools/sync_external_vault.py`.",
        "",
        "| Pack | Group | License | Path | Upstream | Commit |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for r in records:
        lines.append(
            f"| {r['name']} | `{r['group']}` | {r['license']} | `{r['path']}` | {r['url']} | `{r['commit']}` |"
        )
    lines.append("")
    md_text = "\n".join(lines)
    manifest_text = json.dumps({"synced_at": datetime.now(timezone.utc).isoformat(), "packs": records}, indent=2) + "\n"

    if dry_run:
        print(f"[dry-run] Would write THIRD_PARTY_LICENSES.md ({len(records)} entries) and vendor/vendor_manifest.json")
        return

    (ROOT / "THIRD_PARTY_LICENSES.md").write_text(md_text, encoding="utf-8")
    VENDOR_DIR.mkdir(parents=True, exist_ok=True)
    (VENDOR_DIR / "vendor_manifest.json").write_text(manifest_text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Mirror verified CC0/MIT/OFL asset packs into godot4-asset-vault.")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without cloning or writing files.")
    parser.add_argument("--only", nargs="*", choices=["fonts", "audio", "icons", "sprites", "plinkfx"], help="Filter sync groups.")
    args = parser.parse_args()

    selected = set(args.only) if args.only else {"fonts", "audio", "icons", "sprites", "plinkfx"}
    records: list[dict] = []

    for spec in SPECS:
        if spec.group in selected:
            records.append(sync_repo(spec, dry_run=args.dry_run))

    if "plinkfx" in selected:
        pl = run_plinkfx(dry_run=args.dry_run)
        if pl is not None:
            records.append(pl)

    write_licenses_and_manifest(records, dry_run=args.dry_run)
    print(f"Sync complete ({len(records)} packs processed).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
