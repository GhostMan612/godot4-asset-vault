# As Above, So Below. As Within, So Without.
# The Future Dictates the Past and the Past is Always Present.

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import re
import sys
import urllib.parse
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent.parent
VENDOR_DIR = ROOT / "vendor"
PBR_DIR = VENDOR_DIR / "pbr_materials"
PBR_MANIFEST_PATH = VENDOR_DIR / "pbr_manifest.json"
LICENSES_MD_PATH = ROOT / "THIRD_PARTY_LICENSES.md"

USER_AGENT = "godot4-asset-vault/1.0 (+https://github.com/GhostMan612/godot4-asset-vault)"
PBR_SECTION_START = "<!-- CC0_PBR_START -->"
PBR_SECTION_END = "<!-- CC0_PBR_END -->"

DEFAULT_AMBIENTCG_QUERIES: tuple[tuple[str, int], ...] = (
    ("concrete", 3),
    ("cobblestone", 2),
    ("brick", 2),
    ("rust metal", 2),
    ("wood planks", 2),
    ("paper", 2),
    ("stone wall", 2),
)

DEFAULT_POLYHAVEN_KEYWORDS: tuple[tuple[str, int], ...] = (
    ("stone", 2),
    ("concrete", 2),
    ("rust", 2),
    ("wood", 2),
    ("plaster", 2),
)


def fetch_bytes(url: str, timeout: int = 30) -> bytes:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https":
        raise ValueError(f"Non-HTTPS URL blocked: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def fetch_json(url: str, timeout: int = 30) -> dict:
    return json.loads(fetch_bytes(url, timeout=timeout).decode("utf-8"))


def safe_slug(text: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", text.lower()).strip("_")


def write_safe_file(base_dir: Path, filename: str, data: bytes) -> Path:
    clean_name = Path(filename).name
    target = (base_dir / clean_name).resolve()
    base_resolved = base_dir.resolve()
    if not target.is_relative_to(base_resolved):
        raise ValueError(f"Blocked unsafe output path: {filename}")
    target.write_bytes(data)
    return target


def write_godot_standard_material(mat_dir: Path, mat_id: str, maps: dict[str, str]) -> None:
    rel_dir = f"res://vendor/pbr_materials/{mat_id}"
    ext_lines: list[str] = []
    prop_lines: list[str] = []
    idx = 1

    def add_tex(filename: str) -> str:
        nonlocal idx
        res_id = f"{idx}_tex"
        ext_lines.append(f'[ext_resource type="Texture2D" path="{rel_dir}/{filename}" id="{res_id}"]')
        idx += 1
        return res_id

    if "albedo" in maps:
        tid = add_tex(maps["albedo"])
        prop_lines.append(f'albedo_texture = ExtResource("{tid}")')
    if "normal" in maps:
        tid = add_tex(maps["normal"])
        prop_lines.append("normal_enabled = true")
        prop_lines.append(f'normal_texture = ExtResource("{tid}")')
    if "roughness" in maps:
        tid = add_tex(maps["roughness"])
        prop_lines.append(f'roughness_texture = ExtResource("{tid}")')
    if "metallic" in maps:
        tid = add_tex(maps["metallic"])
        prop_lines.append("metallic = 1.0")
        prop_lines.append(f'metallic_texture = ExtResource("{tid}")')
    if "ao" in maps:
        tid = add_tex(maps["ao"])
        prop_lines.append("ao_enabled = true")
        prop_lines.append(f'ao_texture = ExtResource("{tid}")')

    prop_lines.append("texture_filter = 2")
    load_steps = len(ext_lines) + 1
    content = (
        f'[gd_resource type="StandardMaterial3D" load_steps={load_steps} format=3]\n\n'
        + "\n".join(ext_lines)
        + "\n\n[resource]\n"
        + "\n".join(prop_lines)
        + "\n"
    )
    (mat_dir / f"{mat_id}.tres").write_text(content, encoding="utf-8")


def sync_ambientcg(queries: tuple[tuple[str, int], ...], dry_run: bool) -> list[dict]:
    results: list[dict] = []
    seen_ids: set[str] = set()

    for query, limit in queries:
        encoded = urllib.parse.urlencode(
            {
                "type": "Material",
                "include": "downloadData",
                "q": query,
                "limit": str(limit),
            }
        )
        url = f"https://ambientcg.com/api/v2/full_json?{encoded}"
        payload = fetch_json(url)
        for asset in payload.get("foundAssets", []):
            asset_id = asset.get("assetId")
            if not asset_id or asset_id in seen_ids:
                continue
            seen_ids.add(asset_id)

            downloads = (
                asset.get("downloadFolders", {})
                .get("default", {})
                .get("downloadFiletypeCategories", {})
                .get("zip", {})
                .get("downloads", [])
            )
            chosen = next((d for d in downloads if d.get("attribute") == "1K-JPG"), None)
            if not chosen:
                chosen = next((d for d in downloads if d.get("attribute") == "1K-PNG"), None)
            if not chosen or not chosen.get("fullDownloadPath"):
                continue

            mat_id = f"acg_{safe_slug(asset_id)}"
            if dry_run:
                results.append(
                    {
                        "id": mat_id,
                        "provider": "ambientCG",
                        "upstream_id": asset_id,
                        "license": "CC0-1.0",
                        "source_url": f"https://ambientcg.com/view?id={asset_id}",
                        "status": "dry_run",
                    }
                )
                continue

            mat_dir = PBR_DIR / mat_id
            mat_dir.mkdir(parents=True, exist_ok=True)
            zip_bytes = fetch_bytes(chosen["fullDownloadPath"], timeout=60)
            maps: dict[str, str] = {}
            total_bytes = 0

            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                for member in zf.infolist():
                    if member.is_dir():
                        continue
                    fname = Path(member.filename).name
                    lower = fname.lower()
                    role = None
                    if "_color." in lower:
                        role = "albedo"
                    elif "_normalgl." in lower:
                        role = "normal"
                    elif "_roughness." in lower:
                        role = "roughness"
                    elif "_metalness." in lower:
                        role = "metallic"
                    elif "_ambientocclusion." in lower:
                        role = "ao"
                    if role is None:
                        continue
                    raw = zf.read(member)
                    write_safe_file(mat_dir, fname, raw)
                    maps[role] = fname
                    total_bytes += len(raw)

            if "albedo" in maps:
                write_godot_standard_material(mat_dir, mat_id, maps)
                results.append(
                    {
                        "id": mat_id,
                        "provider": "ambientCG",
                        "upstream_id": asset_id,
                        "license": "CC0-1.0",
                        "source_url": f"https://ambientcg.com/view?id={asset_id}",
                        "target": f"vendor/pbr_materials/{mat_id}",
                        "maps": maps,
                        "size_mb": round(total_bytes / (1024 * 1024), 2),
                        "synced_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
                print(f"PACKED: {mat_id} ({len(maps)} maps, {round(total_bytes / (1024 * 1024), 2)} MB)")
    return results


def sync_polyhaven(keywords: tuple[tuple[str, int], ...], dry_run: bool) -> list[dict]:
    results: list[dict] = []
    catalog = fetch_json("https://api.polyhaven.com/assets?t=textures")
    seen_slugs: set[str] = set()

    for keyword, limit in keywords:
        matched = 0
        for slug, meta in catalog.items():
            if matched >= limit:
                break
            if slug in seen_slugs:
                continue
            haystack = " ".join(
                [slug, str(meta.get("name", "")), " ".join(meta.get("tags", [])), " ".join(meta.get("categories", []))]
            ).lower()
            if keyword.lower() not in haystack:
                continue

            seen_slugs.add(slug)
            matched += 1
            mat_id = f"ph_{safe_slug(slug)}"

            if dry_run:
                results.append(
                    {
                        "id": mat_id,
                        "provider": "Poly Haven",
                        "upstream_id": slug,
                        "license": "CC0-1.0",
                        "source_url": f"https://polyhaven.com/a/{slug}",
                        "status": "dry_run",
                    }
                )
                continue

            files_data = fetch_json(f"https://api.polyhaven.com/files/{slug}")
            channel_keys = {
                "albedo": ("Diffuse",),
                "normal": ("nor_gl",),
                "roughness": ("Rough",),
                "ao": ("AO",),
                "metallic": ("Metal",),
            }
            mat_dir = PBR_DIR / mat_id
            mat_dir.mkdir(parents=True, exist_ok=True)
            maps: dict[str, str] = {}
            total_bytes = 0

            for role, keys in channel_keys.items():
                for key in keys:
                    res_block = files_data.get(key, {}).get("1k", {})
                    fmt_block = res_block.get("jpg") or res_block.get("png")
                    if not fmt_block or not fmt_block.get("url"):
                        continue
                    file_url = fmt_block["url"]
                    ext = Path(urllib.parse.urlparse(file_url).path).suffix or ".jpg"
                    fname = f"{mat_id}_{role}{ext}"
                    raw = fetch_bytes(file_url, timeout=45)
                    write_safe_file(mat_dir, fname, raw)
                    maps[role] = fname
                    total_bytes += len(raw)
                    break

            if "albedo" in maps:
                write_godot_standard_material(mat_dir, mat_id, maps)
                results.append(
                    {
                        "id": mat_id,
                        "provider": "Poly Haven",
                        "upstream_id": slug,
                        "license": "CC0-1.0",
                        "source_url": f"https://polyhaven.com/a/{slug}",
                        "target": f"vendor/pbr_materials/{mat_id}",
                        "maps": maps,
                        "size_mb": round(total_bytes / (1024 * 1024), 2),
                        "synced_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
                print(f"PACKED: {mat_id} ({len(maps)} maps, {round(total_bytes / (1024 * 1024), 2)} MB)")
    return results


def update_manifest_and_licenses(records: list[dict]) -> None:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "license": "CC0-1.0",
        "materials": sorted(records, key=lambda r: r["id"]),
    }
    PBR_MANIFEST_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    section_lines = [
        PBR_SECTION_START,
        "## CC0 PBR Materials (Poly Haven & ambientCG)",
        "",
        "| Material ID | Provider | License | Source | Maps | Size (MB) |",
        "| :--- | :--- | :--- | :--- | :--- | ---: |",
    ]
    for rec in payload["materials"]:
        map_list = ", ".join(sorted(rec.get("maps", {}).keys()))
        section_lines.append(
            f"| `{rec['id']}` | {rec['provider']} | {rec['license']} | {rec['source_url']} | "
            f"{map_list} | {rec.get('size_mb', 0.0)} |"
        )
    section_lines.append(PBR_SECTION_END)
    section_block = "\n".join(section_lines) + "\n"

    existing = LICENSES_MD_PATH.read_text(encoding="utf-8") if LICENSES_MD_PATH.exists() else "# Third-Party Licenses\n\n"
    if PBR_SECTION_START in existing and PBR_SECTION_END in existing:
        updated = re.sub(
            rf"{re.escape(PBR_SECTION_START)}.*?{re.escape(PBR_SECTION_END)}\n?",
            section_block,
            existing,
            flags=re.DOTALL,
        )
    else:
        updated = existing.rstrip() + "\n\n" + section_block
    LICENSES_MD_PATH.write_text(updated, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch 1K CC0 PBR materials from ambientCG and Poly Haven.")
    parser.add_argument(
        "--providers",
        nargs="+",
        choices=("ambientcg", "polyhaven", "all"),
        default=["all"],
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    PBR_DIR.mkdir(parents=True, exist_ok=True)

    use_all = "all" in args.providers
    records: list[dict] = []

    if use_all or "ambientcg" in args.providers:
        records.extend(sync_ambientcg(DEFAULT_AMBIENTCG_QUERIES, dry_run=args.dry_run))
    if use_all or "polyhaven" in args.providers:
        records.extend(sync_polyhaven(DEFAULT_POLYHAVEN_KEYWORDS, dry_run=args.dry_run))

    if args.dry_run:
        print(json.dumps(records, indent=2))
        return 0

    update_manifest_and_licenses(records)
    print(f"UPDATED: {PBR_MANIFEST_PATH} ({len(records)} materials) and {LICENSES_MD_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
