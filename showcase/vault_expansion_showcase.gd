extends Control

const SN_ROSTER: Array[Dictionary] = [
	{"name": "Archivist", "path": "res://sovereign_nodes_hd/resources/characters/archivist_sprite_frames.tres"},
	{"name": "Graver", "path": "res://sovereign_nodes_hd/resources/enemies/graver_sprite_frames.tres"},
	{"name": "Obituary Wailer", "path": "res://sovereign_nodes_hd/resources/enemies/obituary_wailer_sprite_frames.tres"},
	{"name": "Contract Breacher", "path": "res://sovereign_nodes_hd/resources/enemies/contract_breacher_sprite_frames.tres"},
	{"name": "Grand Censor", "path": "res://sovereign_nodes_hd/resources/bosses/grand_censor_sprite_frames.tres"},
]

const TPS_UNITS: Array[Dictionary] = [
	{"name": "Operative Carbine", "path": "res://tacplanshooter_hd/sprites/units_8dir/operative_carbine_8dir.png", "x": -1.4},
	{"name": "OpFor Enforcer", "path": "res://tacplanshooter_hd/sprites/units_8dir/opfor_enforcer_8dir.png", "x": 1.4},
]

const PG_TOKENS: Array[String] = [
	"hero_occult_investigator",
	"hero_eldritch_scholar",
	"hero_lantern_warden",
	"hero_void_ranger",
	"monster_star_spawn",
	"monster_shoggoth",
	"monster_void_cultist",
	"monster_astral_hound",
]

var _sn_sprites: Array[AnimatedSprite2D] = []
var _sn_anim_state: StringName = &"walk"
var _tps_camera_pivot: Node3D = null
var _tps_camera: Camera3D = null
var _tps_sprites: Array[Sprite3D] = []
var _auto_orbit: bool = true
var _orbit_yaw: float = 0.0
var _audio_player: AudioStreamPlayer = null

func _ready() -> void:
	var bg := ColorRect.new()
	bg.color = Color(0.08, 0.08, 0.11, 1.0)
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(bg)

	var tabs := TabContainer.new()
	tabs.set_anchors_preset(Control.PRESET_FULL_RECT)
	tabs.offset_left = 12.0
	tabs.offset_top = 12.0
	tabs.offset_right = -12.0
	tabs.offset_bottom = -12.0
	add_child(tabs)

	tabs.add_child(_build_sovereign_nodes_tab())
	tabs.add_child(_build_tacplanshooter_tab())
	tabs.add_child(_build_pathfinder_god_tab())
	tabs.add_child(_build_audio_tab())

func _process(delta: float) -> void:
	if _tps_camera_pivot == null or _tps_camera == null:
		return
	if _auto_orbit:
		_orbit_yaw = fposmod(_orbit_yaw + delta * 0.85, TAU)
		_tps_camera_pivot.rotation.y = _orbit_yaw
	_update_8dir_frames()

func _build_sovereign_nodes_tab() -> Control:
	var root := VBoxContainer.new()
	root.name = "Sovereign-Nodes 2.5D"

	var bar := HBoxContainer.new()
	var walk_btn := Button.new()
	walk_btn.text = "Play Walk"
	walk_btn.pressed.connect(func() -> void: _set_sn_anim(&"walk"))
	bar.add_child(walk_btn)

	var atk_btn := Button.new()
	atk_btn.text = "Play Attack"
	atk_btn.pressed.connect(func() -> void: _set_sn_anim(&"attack"))
	bar.add_child(atk_btn)
	root.add_child(bar)

	var grid := GridContainer.new()
	grid.columns = 2
	grid.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	grid.size_flags_vertical = Control.SIZE_EXPAND_FILL
	root.add_child(grid)

	for entry in SN_ROSTER:
		var card := VBoxContainer.new()
		card.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		card.size_flags_vertical = Control.SIZE_EXPAND_FILL

		var title := Label.new()
		title.text = String(entry["name"])
		title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		card.add_child(title)

		var svc := SubViewportContainer.new()
		svc.stretch = true
		svc.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		svc.size_flags_vertical = Control.SIZE_EXPAND_FILL
		card.add_child(svc)

		var vp := SubViewport.new()
		vp.transparent_bg = false
		vp.size = Vector2i(320, 260)
		svc.add_child(vp)

		var stage := Node2D.new()
		vp.add_child(stage)

		var res_path := String(entry["path"])
		if ResourceLoader.exists(res_path):
			var sprite := AnimatedSprite2D.new()
			sprite.sprite_frames = load(res_path) as SpriteFrames
			sprite.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
			sprite.position = Vector2(160.0, 145.0)
			sprite.play(_sn_anim_state)
			stage.add_child(sprite)
			_sn_sprites.append(sprite)
		else:
			var missing := Label.new()
			missing.text = "Run pack_defect_anim_sheets.py"
			missing.position = Vector2(40.0, 120.0)
			stage.add_child(missing)

		grid.add_child(card)

	var hud_path := "res://sovereign_nodes_hd/ui/archival_hud_sheet.png"
	if ResourceLoader.exists(hud_path):
		var hud := TextureRect.new()
		hud.texture = load(hud_path) as Texture2D
		hud.custom_minimum_size = Vector2(0.0, 180.0)
		hud.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		hud.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		root.add_child(hud)
	return root

func _set_sn_anim(anim_name: StringName) -> void:
	_sn_anim_state = anim_name
	for sprite in _sn_sprites:
		if sprite.sprite_frames != null and sprite.sprite_frames.has_animation(anim_name):
			sprite.play(anim_name)

func _build_tacplanshooter_tab() -> Control:
	var root := VBoxContainer.new()
	root.name = "TacPlanShooter 8-Dir 3D"

	var bar := HBoxContainer.new()
	var orbit_btn := Button.new()
	orbit_btn.text = "Toggle Auto-Orbit"
	orbit_btn.pressed.connect(func() -> void: _auto_orbit = not _auto_orbit)
	bar.add_child(orbit_btn)

	var snap_btn := Button.new()
	snap_btn.text = "Snap +45 deg"
	snap_btn.pressed.connect(func() -> void:
		_auto_orbit = false
		_orbit_yaw = fposmod(_orbit_yaw + deg_to_rad(45.0), TAU)
		if _tps_camera_pivot != null:
			_tps_camera_pivot.rotation.y = _orbit_yaw
	)
	bar.add_child(snap_btn)
	root.add_child(bar)

	var svc := SubViewportContainer.new()
	svc.stretch = true
	svc.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	svc.size_flags_vertical = Control.SIZE_EXPAND_FILL
	root.add_child(svc)

	var vp := SubViewport.new()
	vp.size = Vector2i(960, 540)
	svc.add_child(vp)

	var world := Node3D.new()
	vp.add_child(world)

	var light := DirectionalLight3D.new()
	light.rotation_degrees = Vector3(-50.0, 35.0, 0.0)
	world.add_child(light)

	var floor_mesh := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(10.0, 10.0)
	floor_mesh.mesh = plane
	world.add_child(floor_mesh)

	_tps_camera_pivot = Node3D.new()
	world.add_child(_tps_camera_pivot)

	_tps_camera = Camera3D.new()
	_tps_camera.position = Vector3(0.0, 4.2, 4.4)
	_tps_camera_pivot.add_child(_tps_camera)
	_tps_camera.look_at_from_position(Vector3(0.0, 4.2, 4.4), Vector3(0.0, 0.8, 0.0), Vector3.UP)

	for unit in TPS_UNITS:
		var tex_path := String(unit["path"])
		if not ResourceLoader.exists(tex_path):
			continue
		var spr := Sprite3D.new()
		spr.texture = load(tex_path) as Texture2D
		spr.hframes = 4
		spr.vframes = 2
		spr.pixel_size = 0.0085
		spr.billboard = BaseMaterial3D.BILLBOARD_FIXED_Y
		spr.texture_filter = BaseMaterial3D.TEXTURE_FILTER_NEAREST
		spr.position = Vector3(float(unit["x"]), 1.05, 0.0)
		world.add_child(spr)
		_tps_sprites.append(spr)

	return root

func _update_8dir_frames() -> void:
	if _tps_camera == null:
		return
	var cam_fwd := Vector2(_tps_camera.global_basis.z.x, _tps_camera.global_basis.z.z).normalized()
	var unit_fwd := Vector2(0.0, 1.0)
	var rel_angle := atan2(
		cam_fwd.x * unit_fwd.y - cam_fwd.y * unit_fwd.x,
		cam_fwd.x * unit_fwd.x + cam_fwd.y * unit_fwd.y
	)
	var sector := posmod(int(round(rad_to_deg(rel_angle) / 45.0)), 8)
	for spr in _tps_sprites:
		spr.frame = sector

func _build_audio_tab() -> Control:
	var root := VBoxContainer.new()
	root.name = "Audio Studio"

	var title := Label.new()
	title.text = "Audio cues - tacplanshooter/audio/packed"
	root.add_child(title)

	var script_path := "res://tacplanshooter/audio/packed/audio_cue_registry.gd"
	if not ResourceLoader.exists(script_path):
		var missing := Label.new()
		missing.text = "Run tools/pack_audio_assets.py"
		root.add_child(missing)
		return root

	var reg := load(script_path) as GDScript
	_audio_player = AudioStreamPlayer.new()
	root.add_child(_audio_player)

	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	root.add_child(scroll)
	var list := VBoxContainer.new()
	list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(list)

	for key in reg.CUES.keys():
		var cue: Dictionary = reg.CUES[key]
		var btn := Button.new()
		btn.text = "%s  [%s]  %.2fs" % [String(key), String(cue.get("bus", "SFX")), float(cue.get("duration", 0.0))]
		btn.pressed.connect(func() -> void: _play_cue(reg, StringName(key), cue))
		list.add_child(btn)
	return root

func _play_cue(reg: GDScript, id: StringName, cue: Dictionary) -> void:
	if _audio_player == null:
		return
	var stream: AudioStream = reg.stream_for(id)
	if stream == null:
		return
	_audio_player.stream = stream
	var bus := String(cue.get("bus", "SFX"))
	if AudioServer.get_bus_index(bus) >= 0:
		_audio_player.bus = bus
	else:
		_audio_player.bus = "Master"
	_audio_player.play()

func _build_pathfinder_god_tab() -> Control:
	var scroll := ScrollContainer.new()
	scroll.name = "Pathfinder God Cosmic"

	var vbox := VBoxContainer.new()
	vbox.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(vbox)

	var grid := GridContainer.new()
	grid.columns = 4
	grid.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	vbox.add_child(grid)

	for token_name in PG_TOKENS:
		var token_path := "res://pathfinder_god_hd/tokens/%s.png" % token_name
		var tile := VBoxContainer.new()
		tile.size_flags_horizontal = Control.SIZE_EXPAND_FILL

		var tr := TextureRect.new()
		tr.custom_minimum_size = Vector2(148.0, 148.0)
		tr.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		tr.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		if ResourceLoader.exists(token_path):
			tr.texture = load(token_path) as Texture2D
		tile.add_child(tr)

		var lbl := Label.new()
		lbl.text = token_name.replace("_", " ").capitalize()
		lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		tile.add_child(lbl)
		grid.add_child(tile)

	var hud_path := "res://pathfinder_god_hd/ui/eldritch_hud_sheet.png"
	if ResourceLoader.exists(hud_path):
		var hud_rect := TextureRect.new()
		hud_rect.texture = load(hud_path) as Texture2D
		hud_rect.custom_minimum_size = Vector2(0.0, 320.0)
		hud_rect.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		hud_rect.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		vbox.add_child(hud_rect)

	var pieces := HBoxContainer.new()
	pieces.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	vbox.add_child(pieces)
	for i in range(1, 10):
		var piece_path := "res://pathfinder_god_hd/ui/eldritch_hud_piece_%02d.png" % i
		if not ResourceLoader.exists(piece_path):
			continue
		var piece := TextureRect.new()
		piece.texture = load(piece_path) as Texture2D
		piece.custom_minimum_size = Vector2(96.0, 96.0)
		piece.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		piece.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		pieces.add_child(piece)

	return scroll
