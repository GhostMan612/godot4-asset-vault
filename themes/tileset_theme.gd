# ============================================================
# As Above, So Below. As Within, So Without.
# The Future Dictates the Past and the Past is Always Present.
# ============================================================
class_name TilesetTheme
extends Resource

@export var theme_id: StringName = &"tactical_compound"
@export var tile_size_px: int = 64
@export var floor_tiles: Array[Texture2D] = []
@export var floor_normal: Texture2D = null
@export var wall_top_cap: Texture2D = null
@export var wall_face_variants: Array[Texture2D] = []
@export var wall_normal: Texture2D = null
@export var wall_ao: Texture2D = null
@export var doors: Dictionary = {}
@export var props_atlas: Texture2D = null
@export var ambient_palette: Dictionary = {
	"floor_tint": Color(1, 1, 1, 1),
	"fog_color": Color(0, 0, 0, 0),
	"light_color": Color(1, 1, 1, 1),
	"grid_color": Color(0.06, 0.14, 0.20, 0.14),
}


func floor_tile(index: int) -> Texture2D:
	if floor_tiles.is_empty():
		return null
	return floor_tiles[posmod(index, floor_tiles.size())]


func wall_face(index: int) -> Texture2D:
	if wall_face_variants.is_empty():
		return wall_top_cap
	return wall_face_variants[posmod(index, wall_face_variants.size())]


func door_texture(state: StringName) -> Texture2D:
	var key := String(state).to_upper()
	if key == "BREACHED_DESTROYED":
		key = "BREACHED"
	return doors.get(StringName(key), null) as Texture2D


func color(key: StringName, fallback: Color) -> Color:
	var raw: Variant = ambient_palette.get(String(key), null)
	if raw == null:
		return fallback
	return raw as Color


func is_valid() -> bool:
	if theme_id == &"" or tile_size_px <= 0:
		return false
	if floor_tiles.size() != 4 or floor_normal == null:
		return false
	if wall_top_cap == null or wall_face_variants.size() != 4 or wall_normal == null or wall_ao == null:
		return false
	if props_atlas == null:
		return false
	for key in [&"CLOSED_UNLOCKED", &"LOCKED", &"BARRICADED", &"OPEN", &"BREACHED"]:
		if doors.get(key, null) == null:
			return false
	for key in [&"floor_tint", &"fog_color", &"light_color", &"grid_color"]:
		if not ambient_palette.has(String(key)):
			return false
	return true
