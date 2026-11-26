# ============================================================
# As Above, So Below. As Within, So Without.
# The Future Dictates the Past and the Past is Always Present.
# ============================================================
class_name ModularOperative
extends Node2D


const PALETTE_SWAP_PATH := "res://tacplanshooter_hd/shaders/palette_swap.gdshader"

const SQUADS: Array[Color] = [
	Color(0xEF, 0x44, 0x44), Color(0x3B, 0x82, 0xF6),
	Color(0x22, 0xC5, 0x5E), Color(0xF5, 0x9E, 0x0B),
]


func configure(squad_id: int, role_id: StringName, armor_tier: StringName, weapon_id: StringName) -> void:
	var squad := SQUADS[clampi(squad_id, 0, SQUADS.size() - 1)]
	var trim := Color(1.0, 1.0, 1.0, 1.0)
	var armor := Color(0.6, 0.65, 0.7, 1.0)
	var optic := Color(0.2, 0.4, 0.8, 1.0)
	switch armor_tier:
		&"light": armor = Color(0.7, 0.72, 0.75, 1.0)
		&"heavy": armor = Color(0.5, 0.53, 0.58, 1.0)
		&"ballistic": armor = Color(0.4, 0.45, 0.5, 1.0)
	switch weapon_id:
		&"smg": trim = Color(1.0, 0.85, 0.3, 1.0)
		&"shotgun": trim = Color(1.0, 0.5, 0.2, 1.0)
		&"breach": trim = Color(1.0, 0.2, 0.4, 1.0)
	if role_id == &"MARKSMAN_OVERWATCH" or role_id == &"marksman_overwatch":
		optic = Color(0.1, 0.9, 0.4, 1.0)
	_apply_to_all(squad, trim, armor, optic)


func _apply_to_all(squad: Color, trim: Color, armor: Color, optic: Color) -> void:
	for layer in ["BodyLayer", "VestLayer", "HelmetLayer", "WeaponLayer", "SquadRingLayer"]:
		var s := get_node_or_null(layer)
		if s is CanvasItem:
			_apply_shader(s, squad, trim, armor, optic)
	if get_node_or_null("SquadRingLayer") is Sprite2D:
		var ring = get_node_or_null("SquadRingLayer")
		(ring as Sprite2D).modulate = squad


func _apply_shader(s, squad: Color, trim: Color, armor: Color, optic: Color) -> void:
	if s.material == null or not (s.material is ShaderMaterial):
		var mat := ShaderMaterial.new()
		if ResourceLoader.exists(PALETTE_SWAP_PATH):
			mat.shader = ResourceLoader.load(PALETTE_SWAP_PATH, "Shader")
		s.material = mat
	var mat: ShaderMaterial = s.material as ShaderMaterial
	if mat.shader != null:
		mat.set_shader_parameter("squad_color", squad)
		mat.set_shader_parameter("trim_color", trim)
		mat.set_shader_parameter("armor_color", armor)
		mat.set_shader_parameter("optic_color", optic)
