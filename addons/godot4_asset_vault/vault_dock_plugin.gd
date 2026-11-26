# ============================================================
# As Above, So Below. As Within, So Without.
# The Future Dictates the Past and the Past is Always Present.
# ============================================================
@tool
extends EditorPlugin


var _dock: VBoxContainer = null


func _enter_tree() -> void:
	_dock = VBoxContainer.new()
	_dock.name = "VaultDock"
	_dock.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	add_control_to_bottom_panel(_dock, "Vault")
	_scan()


func _exit_tree() -> void:
	if _dock != null:
		_dock.queue_free()
		_dock = null


func _scan() -> void:
	if _dock == null:
		return
	for p in _dock.get_children():
		p.queue_free()
	var roots := ["res://tacplanshooter", "res://tacplanshooter_hd"]
	for r in roots:
		if not DirAccess.dir_exists_absolute(r):
			continue
		var dir := DirAccess.open(r)
		var files := _scan_dir(r, [])
		for f in files:
			if not _is_wanted(f):
				continue
			var label := Label.new()
			label.text = f.replace("res://", "")
			_dock.add_child(label)


func _is_wanted(path: String) -> bool:
	var ext := path.get_extension().to_lower()
	return ext in [&"tres", &"res", &"png", &"svg", &"tscn"] or (ext == &"tscn" and path.contains("SpriteFrames"))


func _scan_dir(root: String, out: Array) -> Array:
	var acc := out
	var d := DirAccess.open(root)
	if d == null:
		return acc
	d.list_dir_begin()
	var name := d.get_next()
	while name != "":
		var p := root.path_join(name)
		if d.current_is_dir() and not name.begins_with("."):
			acc = _scan_dir(p, acc)
		elif not d.current_is_dir():
			acc.append(p)
		name = d.get_next()
	d.list_dir_end()
	return acc
