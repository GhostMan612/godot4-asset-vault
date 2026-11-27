# Asset Provenance

Theme atlases under `themes/<theme_id>/` are **CC0_CURATED**, packed from verified
artist-drawn CC0 sources via `tools/pack_cc0_themes.py`:

- `tactical_compound`, `industrial_warehouse`, `moonbase_lab` —
  [sparklinlabs/superpowers-asset-packs](https://github.com/sparklinlabs/superpowers-asset-packs)
  (`top-down-shooter/`, `space-shooter/`), CC0 1.0.
- `bank_vault`, `ancestral_crypt` —
  [seloc0des/godot-dungeon-starter](https://github.com/seloc0des/godot-dungeon-starter)
  (`game/art/`, 0x72 DungeonTileset II), CC0.

Normal maps are generated locally from the CC0 albedo via Sobel gradients. Other vault
content is ORIGINAL_PROCEDURAL or CC0/MIT as recorded in `manifest.json` and
`THIRD_PARTY_LICENSES.md`. No unclear-license art is redistributed.
