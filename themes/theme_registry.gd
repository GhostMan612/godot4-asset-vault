# ============================================================
# As Above, So Below. As Within, So Without.
# The Future Dictates the Past and the Past is Always Present.
# ============================================================
class_name ThemeRegistry
extends Object

const DEFAULT_ID: StringName = &"tactical_compound"
const REGISTRY_PATH := "res://addons/godot4-asset-vault/themes/registry.json"


static func for_id(id: StringName) -> TilesetTheme:
	var data := _registry()
	var entries: Array = data.get("themes", [])
	var target := String(id)
	var selected := _entry(entries, target)
	if selected.is_empty():
		target = String(DEFAULT_ID)
		selected = _entry(entries, target)
	return _build(target, selected, data.get("textures", {}))


static func ids() -> Array[StringName]:
	var out: Array[StringName] = []
	for entry in _registry().get("themes", []):
		if typeof(entry) == TYPE_DICTIONARY:
			out.append(StringName(String((entry as Dictionary).get("id", ""))))
	if out.is_empty():
		out.append(DEFAULT_ID)
	return out


static func _entry(entries: Array, id: String) -> Dictionary:
	for entry in entries:
		if typeof(entry) == TYPE_DICTIONARY and String((entry as Dictionary).get("id", "")) == id:
			return entry as Dictionary
	return {}


static func _registry() -> Dictionary:
	var f := FileAccess.open(REGISTRY_PATH, FileAccess.READ)
	if f == null:
		return {}
	var parsed: Variant = JSON.parse_string(f.get_as_text())
	f.close()
	if typeof(parsed) != TYPE_DICTIONARY:
		return {}
	return parsed as Dictionary


static func _build(id: String, entry: Dictionary, textures: Dictionary) -> TilesetTheme:
	var t := TilesetTheme.new()
	t.theme_id = StringName(id)
	var floors: Array[Texture2D] = []
	for path in textures.get("floor", []):
		var tex := _tex(String(path))
		if tex != null:
			floors.append(tex)
	t.floor_tiles = floors
	t.floor_normal = _tex(String(textures.get("floor_normal", "")))
	t.wall_top_cap = _tex(String(textures.get("wall_top_cap", "")))
	var faces: Array[Texture2D] = []
	for path in textures.get("wall_face", []):
		var tex := _tex(String(path))
		if tex != null:
			faces.append(tex)
	t.wall_face_variants = faces
	t.wall_normal = _tex(String(textures.get("wall_normal", "")))
	t.wall_ao = _tex(String(textures.get("wall_ao", "")))
	var door_map: Dictionary = textures.get("doors", {})
	var resolved_doors := {}
	for key in door_map.keys():
		resolved_doors[StringName(String(key))] = _tex(String(door_map[key]))
	t.doors = resolved_doors
	t.props_atlas = _tex(String(textures.get("props_atlas", "")))
	var palette: Dictionary = entry.get("palette", {})
	var ambient := {}
	for key in palette.keys():
		var raw: Array = palette[key]
		ambient[String(key)] = Color(float(raw[0]), float(raw[1]), float(raw[2]), float(raw[3]))
	t.ambient_palette = ambient
	return t


static func _tex(path: String) -> Texture2D:
	if path == "" or not ResourceLoader.exists(path):
		return null
	return ResourceLoader.load(path) as Texture2D
