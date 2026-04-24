@tool
extends RefCounted

var _editor_interface
var _codec: RefCounted


func _init(editor_interface_instance, property_codec: RefCounted) -> void:
	_editor_interface = editor_interface_instance
	_codec = property_codec


func get_edited_scene_root() -> Node:
	return _editor_interface.get_edited_scene_root()


func get_scene_hierarchy() -> Dictionary:
	var root: Node = get_edited_scene_root()
	if root == null:
		return {"status": "error", "error": "No scene is currently open"}
	return {"status": "ok", "data": serialize_node(root, root)}


func get_active_scene() -> Dictionary:
	var root: Node = get_edited_scene_root()
	if root == null:
		return {"status": "error", "error": "No scene is currently open"}
	return {
		"status": "ok",
		"data": {
			"name": root.name,
			"path": root.scene_file_path,
			"type": root.get_class(),
			"rootPath": root.name,
			"instanceId": root.get_instance_id(),
		}
	}


func save_scene(params: Dictionary) -> Dictionary:
	var root: Node = get_edited_scene_root()
	if root == null:
		return {"status": "error", "error": "No scene is currently open"}

	var path: String = str(params.get("path", "")).strip_edges()
	if path != "":
		_editor_interface.save_scene_as(path)
		return {"status": "ok", "data": {"savedTo": path}}

	var err: int = _editor_interface.save_scene()
	if err != OK:
		return {"status": "error", "error": "Failed to save current scene (error %d)" % err}
	return {"status": "ok", "data": {"savedTo": root.scene_file_path}}


func find_node(path: String) -> Node:
	var root: Node = get_edited_scene_root()
	if root == null:
		return null

	path = path.strip_edges()
	if path == "" or path == "." or path == root.name:
		return root

	if path.begins_with(root.name + "/"):
		path = path.substr(root.name.length() + 1)

	var found: Node = root.get_node_or_null(path)
	return found


func serialize_node(node: Node, root: Node = null) -> Dictionary:
	if root == null:
		root = get_edited_scene_root()

	var result: Dictionary = {
		"name": node.name,
		"type": node.get_class(),
		"path": _node_path_for(root, node),
		"instanceId": node.get_instance_id(),
		"visible": node.is_visible_in_tree() if node is CanvasItem or node is Node3D else true,
	}

	if node is Node2D:
		var n2d: Node2D = node
		result["position"] = [n2d.position.x, n2d.position.y]
		result["rotation"] = n2d.rotation_degrees
		result["scale"] = [n2d.scale.x, n2d.scale.y]
	elif node is Node3D:
		var n3d: Node3D = node
		result["position"] = [n3d.position.x, n3d.position.y, n3d.position.z]
		result["rotation"] = [n3d.rotation_degrees.x, n3d.rotation_degrees.y, n3d.rotation_degrees.z]
		result["scale"] = [n3d.scale.x, n3d.scale.y, n3d.scale.z]

	var children: Array[Dictionary] = []
	for child in node.get_children():
		if child is Node:
			var child_node: Node = child
			if child_node.owner != null:
				children.append(serialize_node(child_node, root))
	result["children"] = children
	return result


func list_properties(node: Node) -> Dictionary:
	var properties: Dictionary = {}
	for property_info in node.get_property_list():
		var property_name: String = str(property_info.get("name", ""))
		if property_name == "" or property_name.begins_with("_") or property_name.contains("/"):
			continue
		if int(property_info.get("usage", 0)) & PROPERTY_USAGE_STORAGE == 0:
			continue
		properties[property_name] = _codec.serialize_value(node.get(property_name))

	return {
		"status": "ok",
		"data": {
			"type": node.get_class(),
			"path": _node_path_for(get_edited_scene_root(), node),
			"properties": properties,
		}
	}


func get_property_info(node: Node, property_name: String) -> Dictionary:
	for property_info in node.get_property_list():
		if str(property_info.get("name", "")) == property_name:
			var info: Dictionary = property_info
			return info
	return {}


func _node_path_for(root: Node, node: Node) -> String:
	if root == null or node == null:
		return ""
	if root == node:
		return root.name
	return "%s/%s" % [root.name, str(root.get_path_to(node))]
