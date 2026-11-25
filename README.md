# Godot 4 Asset Vault

Shared, deterministic 2D/UI/shader/audio asset repository for **GhostMan612** Godot 4 games and companion apps.

## Initial Drop: `tacplanshooter/`

Built specifically for **TacPlanShooter** (Godot 4.0, `gl_compatibility` OpenGL ES 3.0, `msaa_2d=0`, portrait Android):

| Folder | Contents |
| --- | --- |
| `tacplanshooter/tilesets/` | `penthouse_floors_tileset.png` (512x256, 8x4 x 64px) & `tactical_walls_cover_tileset.png` (512x256, 8x4 x 64px) |
| `tacplanshooter/resources/` | Ready-to-drop Godot 4.0 `.tres` resources: `penthouse_tileset.tres` (collision polygons pre-wired on physics layer 0), `operators_frames.tres`, `hostiles_frames.tres`, `props_fx_frames.tres` |
| `tacplanshooter/textures/` | 5 seamless 256x256 textures (concrete, penthouse hardwood, metal grate, tactical blueprint grid overlay, fog-of-war value noise) |
| `tacplanshooter/sprites/` | `operators_sheet.png`, `hostiles_sheet.png`, `props_and_fx_sheet.png` (each 256x256, 4x4 x 64px, `+X` Godot 2D forward orientation) |
| `tacplanshooter/ui/icons/` | 20 tactical UI icons in both 64x64 PNG and scalable SVG (`DRAW`/`TAP`, Breach, Flashbang, Smoke, Stairs Up/Down, Briefing/Intel/Roster/Kit/Team, Replay controls, LAN Co-op, Shield, Target, Waypoint, Lock) |
| `tacplanshooter/ui/themes/` | `tactical_hud_theme.tres` dark slate/cyan/amber Godot 4 UI theme |
| `tacplanshooter/shaders/` | 4 `gl_compatibility`-safe `canvas_item` shaders (fog of war, hit flash, blueprint grid, selection pulse) |
| `tacplanshooter/audio/sfx/` | 8 mono 16-bit 44.1 kHz WAV tactical UI & gameplay SFX |

## Godot 4 Import Notes

- **Drop-in `.tres` Resources:** Copy the `tacplanshooter/` folder into your Godot project root so `res://tacplanshooter/...` paths resolve automatically. `penthouse_tileset.tres` maps physics collision layer 0 to all solid walls, closed doors, pillars, and cover while leaving floor tiles and open doorways walkable.
- **Sprites & Tilesets:** Import with `Mipmaps: Off`, `Filter: Linear` (or `Nearest` for crisp pixel lock), `Compress Mode: Lossless` for UI icons and `VRAM Compressed` for 256x256 seamless floor textures.
- **Shaders:** All `.gdshader` files use pure `canvas_item` math with zero MSAA or Forward+ dependencies.

## Regenerating Assets

```bash
pip install pillow
python3 tools/bootstrap_vault.py
```

All outputs are indexed in `manifest.json`.
