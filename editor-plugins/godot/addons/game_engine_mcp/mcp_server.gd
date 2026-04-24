@tool
extends Node

const ConsoleCapturer = preload("console_capturer.gd")

var _tcp_server: TCPServer
var _clients: Array[StreamPeerTCP] = []
var _host: String = "127.0.0.1"
var _port: int = 9879
var _running: bool = false
var _console_capturer: RefCounted


func _ready() -> void:
	_console_capturer = ConsoleCapturer.new()


func start_server(host: String = "", port: int = 0) -> bool:
	if host != "":
		_host = host
	if port > 0:
		_port = port
	_tcp_server = TCPServer.new()
	var err := _tcp_server.listen(_port, _host)
	if err != OK:
		push_error("[GameEngineMCP] Failed to listen on %s:%d (error %d)" % [_host, _port, err])
		return false
	_running = true
	print("[GameEngineMCP] Listening on %s:%d" % [_host, _port])
	return true


func stop_server() -> void:
	_running = false
	for client in _clients:
		client.disconnect_from_host()
	_clients.clear()
	if _tcp_server:
		_tcp_server.stop()
		_tcp_server = null
	print("[GameEngineMCP] Stopped")


func is_running() -> bool:
	return _running


func get_client_count() -> int:
	return _clients.size()


func _process(_delta: float) -> void:
	if not _running or not _tcp_server:
		return
	if _tcp_server.is_connection_available():
		var client := _tcp_server.take_connection()
		_clients.append(client)
		print("[GameEngineMCP] Client connected (%d total)" % _clients.size())

	var to_remove: Array[int] = []
	for i in range(_clients.size()):
		var client: StreamPeerTCP = _clients[i]
		client.poll()
		if client.get_status() != StreamPeerTCP.STATUS_CONNECTED:
			to_remove.append(i)
			continue
		while client.get_available_bytes() > 0:
			var raw: String = client.get_utf8_string()
			if raw == "":
				continue
			for line in raw.split("\n", false):
				var response: String = _handle_message(line.strip_edges())
				client.put_utf8_string(response + "\n")

	for i in to_remove:
		_clients[i].disconnect_from_host()
		_clients.remove_at(i)
	if to_remove.size() > 0:
		print("[GameEngineMCP] Client disconnected (%d remaining)" % _clients.size())


func _handle_message(json_str: String) -> String:
	var parsed: Variant = JSON.parse_string(json_str)
	if parsed == null or not parsed is Dictionary:
		return JSON.stringify({"id": 0, "status": "error", "error": "Invalid JSON"})
	var req: Dictionary = parsed
	var req_id: int = req.get("id", 0)
	var command: String = req.get("command", "")
	var params: Dictionary = req.get("params", {})
	var result: Dictionary = _route_command(command, params)
	result["id"] = req_id
	if not result.has("status"):
		result["status"] = "ok"
	return JSON.stringify(result)


func _route_command(command: String, params: Dictionary) -> Dictionary:
	# Use _ei() helper to avoid repeating the untyped EditorInterface access.
	var ei = _ei()
	match command:
		"ping":
			return _cmd_ping()
		"get_editor_info":
			return _cmd_get_editor_info(ei)
		"play":
			ei.play_main_scene()
			return {"status": "ok", "data": {"playing": true}}
		"pause":
			if ei.is_playing_scene():
				Engine.set_time_scale(0.0)
				return {"status": "ok", "data": {"paused": true}}
			return {"status": "error", "error": "Not currently playing"}
		"stop":
			ei.stop_playing_scene()
			return {"status": "ok", "data": {"playing": false}}
		"get_console_logs":
			return _console_capturer.get_console_logs(params)
		"clear_console":
			return _console_capturer.clear_console()
		"get_scene_hierarchy":
			var edited = ei.get_edited_scene_root()
			if edited == null:
				return {"status": "error", "error": "No scene is currently open"}
			return {"status": "ok", "data": _serialize_node(edited)}
		"get_active_scene":
			var edited2 = ei.get_edited_scene_root()
			if edited2 == null:
				return {"status": "error", "error": "No scene is currently open"}
			return {"status": "ok", "data": {"name": edited2.name, "path": edited2.scene_file_path, "type": edited2.get_class()}}
		"save_scene":
			return _cmd_save_scene(ei, params)
		"get_object":
			return _cmd_get_object(ei, params)
		"create_object":
			return _cmd_create_object(ei, params)
		"delete_object":
			return _cmd_delete_object(params)
		"move_object":
			return _cmd_move_object(params)
		"get_properties":
			return _cmd_get_properties(params)
		"set_property":
			return _cmd_set_property(params)
		"set_properties":
			return _cmd_set_properties(params)
		"list_assets":
			return _cmd_list_assets(params)
		"take_screenshot":
			return _cmd_take_screenshot(ei)
		"execute_code":
			return _cmd_execute_code(params)
		_:
			return {"status": "error", "error": "Unknown command: " + command}


## Untyped accessor for the EditorInterface singleton.
## GDScript cannot assign the class (GDScriptNativeClass) to a typed variable,
## so we return it untyped and let duck typing do the work.
func _ei():
	return EditorInterface


# --- Command implementations ---

func _cmd_ping() -> Dictionary:
	return {"status": "ok", "data": {"status": "alive", "engine": "godot", "version": Engine.get_version_info().string}}


func _cmd_get_editor_info(ei) -> Dictionary:
	return {
		"status": "ok",
		"data": {
			"engine": "godot",
			"version": Engine.get_version_info().string,
			"platform": OS.get_name(),
			"projectName": ProjectSettings.get_setting("application/config/name", "Unknown"),
			"projectPath": ProjectSettings.globalize_path("res://"),
			"isPlaying": ei.is_playing_scene(),
		}
	}


func _cmd_save_scene(ei, params: Dictionary) -> Dictionary:
	var path: String = params.get("path", "")
	var edited: Node = ei.get_edited_scene_root()
	if edited == null:
		return {"status": "error", "error": "No scene is currently open"}
	if path != "":
		var err: int = edited.owner.save_scene_file(path)
		if err != OK:
			return {"status": "error", "error": "Failed to save to %s (error %d)" % [path, err]}
		return {"status": "ok", "data": {"savedTo": path}}
	ei.save_scene()
	return {"status": "ok", "data": {"savedTo": edited.scene_file_path}}


func _cmd_get_object(ei, params: Dictionary) -> Dictionary:
	var path: String = params.get("path", "")
	var edited: Node = ei.get_edited_scene_root()
	var node: Node = _find_node(edited, path)
	if node == null:
		return {"status": "error", "error": "Node not found: '%s'" % path}
	return {"status": "ok", "data": _serialize_node(node)}


func _cmd_create_object(ei, params: Dictionary) -> Dictionary:
	var name: String = params.get("name", "NewNode")
	var type: String = params.get("type", "Node")
	var parent_path: String = params.get("parent", "")
	var edited: Node = ei.get_edited_scene_root()
	if edited == null:
		return {"status": "error", "error": "No scene is currently open"}
	var parent: Node = _find_node(edited, parent_path) if parent_path != "" else edited
	if parent == null:
		return {"status": "error", "error": "Parent not found: '%s'" % parent_path}
	var new_node: Node = _instantiate_type(type)
	new_node.name = name
	parent.add_child(new_node)
	new_node.owner = edited
	return {"status": "ok", "data": {"name": new_node.name, "type": new_node.get_class()}}


func _cmd_delete_object(params: Dictionary) -> Dictionary:
	var path: String = params.get("path", "")
	var edited: Node = _ei().get_edited_scene_root()
	var node: Node = _find_node(edited, path)
	if node == null:
		return {"status": "error", "error": "Node not found: '%s'" % path}
	if node == edited:
		return {"status": "error", "error": "Cannot delete the scene root"}
	var node_name: String = node.name
	node.get_parent().remove_child(node)
	node.queue_free()
	return {"status": "ok", "data": {"deleted": node_name}}


func _cmd_move_object(params: Dictionary) -> Dictionary:
	var path: String = params.get("path", "")
	var edited: Node = _ei().get_edited_scene_root()
	var node: Node = _find_node(edited, path)
	if node == null:
		return {"status": "error", "error": "Node not found: '%s'" % path}

	var parent_path: String = params.get("parent", "")
	if parent_path != "":
		var new_parent: Node = _find_node(edited, parent_path)
		if new_parent == null:
			return {"status": "error", "error": "Parent not found: '%s'" % parent_path}
		node.reparent(new_parent)

	# Transform - position
	var pos_arr = params.get("position")
	if pos_arr is Array and pos_arr.size() >= 2:
		if node is Node2D:
			(node as Node2D).position = Vector2(float(pos_arr[0]), float(pos_arr[1]))
		elif node is Node3D and pos_arr.size() >= 3:
			(node as Node3D).position = Vector3(float(pos_arr[0]), float(pos_arr[1]), float(pos_arr[2]))

	# Transform - rotation
	# Note: Node2D.rotation_degrees is a single float in Godot 4, not Vector2.
	var rot_arr = params.get("rotation")
	if rot_arr is Array and rot_arr.size() >= 3:
		if node is Node3D:
			(node as Node3D).rotation_degrees = Vector3(float(rot_arr[0]), float(rot_arr[1]), float(rot_arr[2]))
	elif rot_arr is Array and rot_arr.size() >= 1:
		if node is Node2D:
			(node as Node2D).rotation_degrees = float(rot_arr[0])

	# Transform - scale
	var scl_arr = params.get("scale")
	if scl_arr is Array and scl_arr.size() >= 2:
		if node is Node2D:
			(node as Node2D).scale = Vector2(float(scl_arr[0]), float(scl_arr[1]))
		elif node is Node3D and scl_arr.size() >= 3:
			(node as Node3D).scale = Vector3(float(scl_arr[0]), float(scl_arr[1]), float(scl_arr[2]))

	var result: Dictionary = {"name": node.name}
	if node is Node2D:
		var n2d: Node2D = node as Node2D
		result["position"] = [n2d.position.x, n2d.position.y]
		result["rotation"] = n2d.rotation_degrees
		result["scale"] = [n2d.scale.x, n2d.scale.y]
	elif node is Node3D:
		var n3d: Node3D = node as Node3D
		result["position"] = [n3d.position.x, n3d.position.y, n3d.position.z]
		result["rotation"] = [n3d.rotation_degrees.x, n3d.rotation_degrees.y, n3d.rotation_degrees.z]
		result["scale"] = [n3d.scale.x, n3d.scale.y, n3d.scale.z]
	return {"status": "ok", "data": result}


func _cmd_get_properties(params: Dictionary) -> Dictionary:
	var path: String = params.get("path", "")
	var edited: Node = _ei().get_edited_scene_root()
	var node: Node = _find_node(edited, path)
	if node == null:
		return {"status": "error", "error": "Node not found: '%s'" % path}
	var props: Dictionary = {}
	for prop in node.get_property_list():
		var pname: String = prop["name"]
		if pname.begins_with("_") or pname.contains("/"):
			continue
		if prop["usage"] & PROPERTY_USAGE_STORAGE == 0:
			continue
		var val: Variant = node.get(pname)
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
		props[pname] = val
	return {"status": "ok", "data": {"properties": props, "type": node.get_class()}}


func _cmd_set_property(params: Dictionary) -> Dictionary:
	var path: String = params.get("path", "")
	var property: String = params.get("property", "")
	var value: Variant = params.get("value")
	var edited: Node = _ei().get_edited_scene_root()
	var node: Node = _find_node(edited, path)
	if node == null:
		return {"status": "error", "error": "Node not found: '%s'" % path}
	var err: int = _apply_property(node, property, value)
	if err != OK:
		return {"status": "error", "error": "Failed to set '%s' on '%s'" % [property, path]}
	return {"status": "ok", "data": {"path": path, "property": property, "value": value}}


func _cmd_set_properties(params: Dictionary) -> Dictionary:
	var path: String = params.get("path", "")
	var properties: Dictionary = params.get("properties", {})
	var edited: Node = _ei().get_edited_scene_root()
	var node: Node = _find_node(edited, path)
	if node == null:
		return {"status": "error", "error": "Node not found: '%s'" % path}
	var set_keys: Array = []
	var failed: Array = []
	for key in properties:
		var err: int = _apply_property(node, key, properties[key])
		if err == OK:
			set_keys.append(key)
		else:
			failed.append(key)
	return {"status": "ok", "data": {"set": set_keys, "failed": failed}}


func _cmd_list_assets(params: Dictionary) -> Dictionary:
	var path: String = params.get("path", "res://")
	var da: DirAccess = DirAccess.open(path)
	if da == null:
		return {"status": "error", "error": "Cannot open path: '%s'" % path}
	var assets: Array[Dictionary] = []
	da.list_dir_begin()
	var file_name: String = da.get_next()
	while file_name != "":
		if not file_name.begins_with("."):
			var full_path: String = path.path_join(file_name)
			var is_dir: bool = da.current_is_dir()
			assets.append({"name": file_name.get_basename(), "path": full_path, "type": "Directory" if is_dir else file_name.get_extension()})
		file_name = da.get_next()
	da.list_dir_end()
	return {"status": "ok", "data": {"assets": assets, "count": assets.size(), "path": path}}


func _cmd_take_screenshot(ei) -> Dictionary:
	# Try 3D viewports (indexed 0-3)
	var vp: SubViewport = null
	for i in range(4):
		var candidate: SubViewport = ei.get_editor_viewport_3d(i)
		if candidate != null:
			vp = candidate
			break
	# Fall back to 2D viewport (no index argument in Godot 4.6)
	if vp == null:
		vp = ei.get_editor_viewport_2d()
	if vp == null:
		return {"status": "error", "error": "No viewport available"}
	var img: Image = vp.get_texture().get_image()
	if img == null:
		return {"status": "error", "error": "Failed to capture viewport"}
	var png_data: PackedByteArray = img.save_png_to_buffer()
	var base64: String = Marshalls.raw_to_base64(png_data)
	return {"status": "ok", "data": {"image_base64": base64, "width": img.get_width(), "height": img.get_height(), "format": "png"}}


func _cmd_execute_code(params: Dictionary) -> Dictionary:
	var code: String = params.get("code", "")
	if code == "":
		return {"status": "error", "error": "No code provided"}
	var expr := Expression.new()
	var err: int = expr.parse(code)
	if err != OK:
		return {"status": "ok", "data": {"error": "Parse error: " + expr.get_error_text(), "language": "gdscript"}}
	var result: Variant = expr.execute()
	if expr.has_execute_failed():
		return {"status": "ok", "data": {"error": expr.get_error_text(), "language": "gdscript"}}
	var output: String = str(result) if result != null else "(null)"
	return {"status": "ok", "data": {"output": output, "language": "gdscript"}}


# --- Helpers ---

func _find_node(root: Node, path: String) -> Node:
	if root == null:
		return null
	if path == "" or path == root.name:
		return root
	var node: Node = root.get_node_or_null(path)
	if node != null:
		return node
	return _find_node_recursive(root, path)


func _find_node_recursive(node: Node, name: String) -> Node:
	if node.name == name:
		return node
	for child in node.get_children():
		var found: Node = _find_node_recursive(child, name)
		if found != null:
			return found
	return null


func _serialize_node(node: Node) -> Dictionary:
	var result: Dictionary = {"name": node.name, "type": node.get_class(), "visible": node.is_visible_in_tree() if node.is_inside_tree() else true}
	if node is Node2D:
		var n2d: Node2D = node as Node2D
		result["position"] = [n2d.position.x, n2d.position.y]
		result["rotation"] = n2d.rotation_degrees  # float, not Vector2
		result["scale"] = [n2d.scale.x, n2d.scale.y]
	elif node is Node3D:
		var n3d: Node3D = node as Node3D
		result["position"] = [n3d.position.x, n3d.position.y, n3d.position.z]
		result["rotation"] = [n3d.rotation_degrees.x, n3d.rotation_degrees.y, n3d.rotation_degrees.z]
		result["scale"] = [n3d.scale.x, n3d.scale.y, n3d.scale.z]
	var children: Array[Dictionary] = []
	for child in node.get_children():
		if child.owner != null:
			children.append(_serialize_node(child))
	result["children"] = children
	return result


func _instantiate_type(type: String) -> Node:
	match type.to_lower():
		"node2d": return Node2D.new()
		"node3d", "spatial": return Node3D.new()
		"characterbody2d": return CharacterBody2D.new()
		"characterbody3d": return CharacterBody3D.new()
		"rigidbody2d": return RigidBody2D.new()
		"rigidbody3d": return RigidBody3D.new()
		"camera2d": return Camera2D.new()
		"camera3d": return Camera3D.new()
		"sprite2d": return Sprite2D.new()
		"collisionshape2d": return CollisionShape2D.new()
		"collisionshape3d": return CollisionShape3D.new()
		"area2d": return Area2D.new()
		"area3d": return Area3D.new()
		"audiostreamplayer": return AudioStreamPlayer.new()
		"light2d": return PointLight2D.new()
		"light3d": return DirectionalLight3D.new()
		"cube":
			var mi := MeshInstance3D.new()
			mi.mesh = BoxMesh.new()
			return mi
		"meshinstance3d": return MeshInstance3D.new()
		_:
			if ClassDB.class_exists(type):
				var inst: Node = ClassDB.instantiate(type) as Node
				if inst != null:
					return inst
			return Node.new()


func _apply_property(node: Node, property: String, value: Variant) -> int:
	if value == null:
		return ERR_INVALID_PARAMETER
	var current: Variant = node.get(property)
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
			node.set(property, Color.from_string(value, Color.WHITE))
		else:
			node.set(property, value)
	else:
		node.set(property, value)
	return OK
