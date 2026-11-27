class_name Sprite3D8DirBillboard
extends Sprite3D

@export var facing_yaw_rad: float = 0.0

func _ready() -> void:
	hframes = 4
	vframes = 2
	billboard = BaseMaterial3D.BILLBOARD_FIXED_Y
	texture_filter = BaseMaterial3D.TEXTURE_FILTER_NEAREST
	alpha_cut = SpriteBase3D.ALPHA_CUT_DISCARD
	alpha_scissor_threshold = 0.5

func update_facing_for_camera(cam: Camera3D, unit_yaw_rad: float) -> void:
	facing_yaw_rad = unit_yaw_rad
	if cam == null:
		return
	var cam_fwd := Vector2(cam.global_basis.z.x, cam.global_basis.z.z).normalized()
	var unit_fwd := Vector2(sin(facing_yaw_rad), cos(facing_yaw_rad)).normalized()
	var rel_angle := atan2(
		cam_fwd.x * unit_fwd.y - cam_fwd.y * unit_fwd.x,
		cam_fwd.x * unit_fwd.x + cam_fwd.y * unit_fwd.y
	)
	var sector := int(round(rad_to_deg(rel_angle) / 45.0))
	frame = posmod(sector, 8)
