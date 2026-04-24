@tool
class_name Commands
extends RefCounted


static func ping() -> Dictionary:
	return {"status": "ok", "data": {"status": "alive", "engine": "godot", "version": Engine.get_version_info().string}}


static func get_editor_info() -> Dictionary:
	var ei := EditorInterface.singleton()
	return {
		"status": "ok",
		"data": {
			"engine": "godot",
			"version": Engine.get_version_info().string,
			"platform": OS.get_name(),
			"projectName": ProjectSettings.get_setting("application/config/name", "Unknown"),
			"projectPath": ProjectSettings.globalize_path("res://"),
			"isPlaying": EditorInterface.singleton().is_playing_scene(),
		}
	}


static func play() -> Dictionary:
	EditorInterface.singleton().play_main_scene()
	return {"status": "ok", "data": {"playing": true}}


static func pause() -> Dictionary:
	EditorInterface.singleton().set_pause_on_lost_focus(false)
	if EditorInterface.singleton().is_playing_scene():
		Engine.set_time_scale(0.0)
		return {"status": "ok", "data": {"paused": true}}
	return {"status": "error", "error": "Not currently playing"}


static func stop() -> Dictionary:
	EditorInterface.singleton().stop_playing_scene()
	return {"status": "ok", "data": {"playing": false}}


static func get_scene_hierarchy() -> Dictionary:
	var edited := EditorInterface.singleton().get_edited_scene_root()
	if edited == null:
		return {"status": "error", "error": "No scene is currently open"}

	var tree := _serialize_node(edited)
	return {"status": "ok", "data": tree}


static func get_active_scene() -> Dictionary:
	var edited := EditorInterface.singleton().get_edited_scene_root()
	if edited == null:
		return {"status": "error", "error": "No scene is currently open"}

	return {
		"status": "ok",
		"data": {
			"name": edited.name,
			"path": edited.scene_file_path,
			"type": edited.get_class(),
		}
	}


static func save_scene(params: Dictionary) -> Dictionary:
	var path: String = params.get("path", "")
	var edited := EditorInterface.singleton().get_edited_scene_root()
	if edited == null:
		return {"status": "error", "error": "No scene is currently open"}

	if path != "":
		var err := edited.owner.save_scene_file(path)
		if err != OK:
			return {"status": "error", "error": "Failed to save to %s (error %d)" % [path, err]}
		return {"status": "ok", "data": {"savedTo": path}}

	EditorInterface.singleton().save_scene()
	return {"status": "ok", "data": {"savedTo": edited.scene_file_path}}


static func get_object(params: Dictionary) -> Dictionary:
	var path: String = params.get("path", "")
	var node := _find_node(path)
	if node == null:
		return {"status": "error", "error": "Node not found: '%s'" % path}

	return {"status": "ok", "data": _serialize_node(node)}


static func create_object(params: Dictionary) -> Dictionary:
	var name: String = params.get("name", "NewNode")
	var type: String = params.get("type", "Node")
	var parent_path: String = params.get("parent", "")

	var parent: Node = _find_node(parent_path) if parent_path != "" else EditorInterface.singleton().get_edited_scene_root()
	if parent == null:
		return {"status": "error", "error": "Parent not found: '%s'" % parent_path}

	var new_node: Node = null
	# Map common type names to Godot classes
	match type.to_lower():
		"node2d":
			new_node = Node2D.new()
		"node3d", "spatial":
			new_node = Node3D.new()
		"characterbody2d":
			new_node = CharacterBody2D.new()
		"characterbody3d":
			new_node = CharacterBody3D.new()
		"rigidbody2d":
			new_node = RigidBody2D.new()
		"rigidbody3d":
			new_node = RigidBody3D.new()
		"camera2d":
			new_node = Camera2D.new()
		"camera3d":
			new_node = Camera3D.new()
		"sprite2d":
			new_node = Sprite2D.new()
		"sprite3d":
			new_node = Sprite3D.new()
		"meshinstance3d", "cube":
			new_node = MeshInstance3D.new()
			if type.to_lower() == "cube":
				new_node.mesh = BoxMesh.new()
		"collisionshape2d":
			new_node = CollisionShape2D.new()
		"collisionshape3d":
			new_node = CollisionShape3D.new()
		"area2d":
			new_node = Area2D.new()
		"area3d":
			new_node = Area3D.new()
		"audioplayer", "audiostreamplayer":
			new_node = AudioStreamPlayer.new()
		"light2d":
			new_node = PointLight2D.new()
		"light3d":
			new_node = DirectionalLight3D.new()
		_:
			# Try to instantiate by class name
			if ClassDB.class_exists(type):
				new_node = ClassDB.instantiate(type) as Node
			if new_node == null:
				new_node = Node.new()

	new_node.name = name
	parent.add_child(new_node)
	new_node.owner = EditorInterface.singleton().get_edited_scene_root()

	return {"status": "ok", "data": {"name": new_node.name, "type": new_node.get_class()}}


static func delete_object(params: Dictionary) -> Dictionary:
	var path: String = params.get("path", "")
	var node := _find_node(path)
	if node == null:
		return {"status": "error", "error": "Node not found: '%s'" % path}

	var node_name := node.name
	node.queue_free()
	return {"status": "ok", "data": {"deleted": node_name}}


static func move_object(params: Dictionary) -> Dictionary:
	var path: String = params.get("path", "")
	var node := _find_node(path)
	if node == null:
		return {"status": "error", "error": "Node not found: '%s'" % path}

	# Reparent
	var parent_path: String = params.get("parent", "")
	if parent_path != "":
		var new_parent := _find_node(parent_path)
		if new_parent == null:
			return {"status": "error", "error": "Parent not found: '%s'" % parent_path}
		node.reparent(new_parent)

	# Transform (for Node2D/Node3D)
	var position = params.get("position")
	if position != null and position is Array and position.size() >= 2:
		if node is Node2D:
			node.position = Vector2(float(position[0]), float(position[1]))
		elif node is Node3D:
			var z := float(position[2]) if position.size() >= 3 else 0.0
			node.position = Vector3(float(position[0]), float(position[1]), z)

	var rotation = params.get("rotation")
	if rotation != null and rotation is Array and rotation.size() >= 2:
		if node is Node2D:
			node.rotation_degrees = Vector2(float(rotation[0]), float(rotation[1]))
		elif node is Node3D:
			var rz := float(rotation[2]) if rotation.size() >= 3 else 0.0
			node.rotation_degrees = Vector3(float(rotation[0]), float(rotation[1]), rz)

	var scale = params.get("scale")
	if scale != null and scale is Array and scale.size() >= 2:
		if node is Node2D:
			node.scale = Vector2(float(scale[0]), float(scale[1]))
		elif node is Node3D:
			var sz := float(scale[2]) if scale.size() >= 3 else 1.0
			node.scale = Vector3(float(scale[0]), float(scale[1]), sz)

	var result: Dictionary = {"name": node.name}
	if node is Node2D:
		result["position"] = [node.position.x, node.position.y]
		result["rotation"] = [node.rotation_degrees.x, node.rotation_degrees.y]
		result["scale"] = [node.scale.x, node.scale.y]
	elif node is Node3D:
		result["position"] = [node.position.x, node.position.y, node.position.z]
		result["rotation"] = [node.rotation_degrees.x, node.rotation_degrees.y, node.rotation_degrees.z]
		result["scale"] = [node.scale.x, node.scale.y, node.scale.z]

	return {"status": "ok", "data": result}


static func get_properties(params: Dictionary) -> Dictionary:
	var path: String = params.get("path", "")
	var node := _find_node(path)
	if node == null:
		return {"status": "error", "error": "Node not found: '%s'" % path}

	var props: Dictionary = {}
	for prop in node.get_property_list():
		var name: String = prop["name"]
		if name.begins_with("_") or name.contains("/"):
			continue
		if prop["usage"] & PROPERTY_USAGE_STORAGE == 0:
			continue
		var val = node.get(name)
		if val is Resource or val is Node:
			val = str(val)
		elif val is Vector2:
			val = [val.x, val.y]
		elif val is Vector3:
			val = [val.x, val.y, val.z]
		elif val is Color:
			val = "#" + val.to_html()
		elif val is Array or val is Dictionary:
			val = str(val)
		props[name] = val

	return {"status": "ok", "data": {"properties": props, "type": node.get_class()}}


static func set_property(params: Dictionary) -> Dictionary:
	var path: String = params.get("path", "")
	var property: String = params.get("property", "")
	var value = params.get("value")

	var node := _find_node(path)
	if node == null:
		return {"status": "error", "error": "Node not found: '%s'" % path}

	var err := _apply_property(node, property, value)
	if err != OK:
		return {"status": "error", "error": "Failed to set '%s' on '%s'" % [property, path]}

	return {"status": "ok", "data": {"path": path, "property": property, "value": value}}


static func set_properties(params: Dictionary) -> Dictionary:
	var path: String = params.get("path", "")
	var properties: Dictionary = params.get("properties", {})

	var node := _find_node(path)
	if node == null:
		return {"status": "error", "error": "Node not found: '%s'" % path}

	var set_keys: Array = []
	var failed: Array = []
	for key in properties:
		var err := _apply_property(node, key, properties[key])
		if err == OK:
			set_keys.append(key)
		else:
			failed.append(key)

	return {"status": "ok", "data": {"set": set_keys, "failed": failed}}


static func list_assets(params: Dictionary) -> Dictionary:
	var path: String = params.get("path", "res://")
	var ei := EditorInterface.singleton()
	var da := DirAccess.open(path)
	if da == null:
		return {"status": "error", "error": "Cannot open path: '%s'" % path}

	var assets: Array[Dictionary] = []
	da.list_dir_begin()
	var file_name := da.get_next()
	while file_name != "":
		if not file_name.begins_with("."):
			var full_path := path.path_join(file_name)
			var is_dir := da.current_is_dir()
			assets.append({
				"name": file_name.get_basename(),
				"path": full_path,
				"type": "Directory" if is_dir else file_name.get_extension(),
			})
		file_name = da.get_next()
	da.list_dir_end()

	return {"status": "ok", "data": {"assets": assets, "count": assets.size(), "path": path}}


static func take_screenshot() -> Dictionary:
	# Godot editor viewport screenshot
	var vp := EditorInterface.singleton().get_editor_viewport_3d(0)
	if vp == null:
		vp = EditorInterface.singleton().get_editor_viewport_2d(0)
	if vp == null:
		return {"status": "error", "error": "No viewport available"}

	var img := vp.get_texture().get_image()
	if img == null:
		return {"status": "error", "error": "Failed to capture viewport"}

	var png_data := img.save_png_to_buffer()
	var base64 := Marshalls.raw_to_base64(png_data)

	return {"status": "ok", "data": {"image_base64": base64, "width": img.get_width(), "height": img.get_height(), "format": "png"}}


static func execute_code(params: Dictionary) -> Dictionary:
	var code: String = params.get("code", "")
	if code == "":
		return {"status": "error", "error": "No code provided"}

	# Execute GDScript using Expression
	var expr := Expression.new()
	var err := expr.parse(code)
	if err != OK:
		return {"status": "ok", "data": {"error": "Parse error: " + expr.get_error_text(), "language": "gdscript"}}

	var result = expr.execute()
	if expr.has_execute_failed():
		return {"status": "ok", "data": {"error": expr.get_error_text(), "language": "gdscript"}}

	return {"status": "ok", "data": {"output": str(result) if result != null else "(null)", "language": "gdscript"}}


# --- Helpers ---

static func _find_node(path: String) -> Node:
	var edited := EditorInterface.singleton().get_edited_scene_root()
	if edited == null:
		return null

	if path == "" or path == edited.name:
		return edited

	# Try direct path
	var node := edited.get_node_or_null(path)
	if node != null:
		return node

	# Try finding by name anywhere in tree
	return _find_node_recursive(edited, path)


static func _find_node_recursive(node: Node, name: String) -> Node:
	if node.name == name:
		return node
	for child in node.get_children():
		var found := _find_node_recursive(child, name)
		if found != null:
			return found
	return null


static func _serialize_node(node: Node) -> Dictionary:
	var result: Dictionary = {
		"name": node.name,
		"type": node.get_class(),
		"visible": node.is_visible_in_tree() if node.is_inside_tree() else true,
	}

	# Transform info
	if node is Node2D:
		result["position"] = [node.position.x, node.position.y]
		result["rotation"] = [node.rotation_degrees.x, node.rotation_degrees.y]
		result["scale"] = [node.scale.x, node.scale.y]
	elif node is Node3D:
		result["position"] = [node.position.x, node.position.y, node.position.z]
		result["rotation"] = [node.rotation_degrees.x, node.rotation_degrees.y, node.rotation_degrees.z]
		result["scale"] = [node.scale.x, node.scale.y, node.scale.z]

	# Children
	var children: Array[Dictionary] = []
	for child in node.get_children():
		if child.owner != null:  # Only include scene-owned nodes
			children.append(_serialize_node(child))
	result["children"] = children

	return result


static func _apply_property(node: Node, property: String, value) -> int:
	if value == null:
		return ERR_INVALID_PARAMETER

	var current = node.get(property)
	if current == null and not node.property_can_revert(property):
		# Try setting anyway
		node.set(property, value)
		return OK

	# Type coercion
	if current is float:
		node.set(property, float(value))
	elif current is int:
		node.set(property, int(value))
	elif current is bool:
		node.set(property, bool(value))
	elif current is String:
		node.set(property, str(value))
	elif current is Vector2 and value is Array and value.size() >= 2:
		node.set(property, Vector2(float(value[0]), float(value[1])))
	elif current is Vector3 and value is Array and value.size() >= 3:
		node.set(property, Vector3(float(value[0]), float(value[1]), float(value[2])))
	elif current is Color:
		if value is String:
			var c := Color.from_string(value, Color.WHITE)
			node.set(property, c)
		else:
			node.set(property, value)
	else:
		node.set(property, value)

	return OK
