@tool
extends RefCounted

var _scene_service: RefCounted
var _undo_service: RefCounted
var _codec: RefCounted


func _init(scene_service: RefCounted, undo_service: RefCounted, property_codec: RefCounted) -> void:
	_scene_service = scene_service
	_undo_service = undo_service
	_codec = property_codec


func get_object(params: Dictionary) -> Dictionary:
	var path: String = str(params.get("path", ""))
	var node: Node = _scene_service.find_node(path)
	if node == null:
		return {"status": "error", "error": "Node not found: '%s'" % path}
	return {"status": "ok", "data": _scene_service.serialize_node(node)}


func create_object(params: Dictionary) -> Dictionary:
	var root: Node = _scene_service.get_edited_scene_root()
	if root == null:
		return {"status": "error", "error": "No scene is currently open"}

	var node_name: String = str(params.get("name", "NewNode")).strip_edges()
	var type_name: String = str(params.get("type", "Node")).strip_edges()
	var parent_path: String = str(params.get("parent", "")).strip_edges()
	var parent: Node = root if parent_path == "" else _scene_service.find_node(parent_path)
	if parent == null:
		return {"status": "error", "error": "Parent not found: '%s'" % parent_path}

	var instance: Node = _instantiate_type(type_name)
	if instance == null:
		return {"status": "error", "error": "Unsupported or invalid node type: '%s'" % type_name}

	instance.name = node_name if node_name != "" else "NewNode"
	_undo_service.create_node_action("Create %s" % instance.name, parent, instance, root)
	return {"status": "ok", "data": _scene_service.serialize_node(instance)}


func delete_object(params: Dictionary) -> Dictionary:
	var root: Node = _scene_service.get_edited_scene_root()
	if root == null:
		return {"status": "error", "error": "No scene is currently open"}

	var path: String = str(params.get("path", ""))
	var node: Node = _scene_service.find_node(path)
	if node == null:
		return {"status": "error", "error": "Node not found: '%s'" % path}
	if node == root:
		return {"status": "error", "error": "Cannot delete the scene root"}

	var node_name: String = node.name
	_undo_service.delete_node_action("Delete %s" % node_name, node)
	return {"status": "ok", "data": {"deleted": node_name, "path": path}}


func move_object(params: Dictionary) -> Dictionary:
	var path: String = str(params.get("path", ""))
	var node: Node = _scene_service.find_node(path)
	if node == null:
		return {"status": "error", "error": "Node not found: '%s'" % path}

	var root: Node = _scene_service.get_edited_scene_root()
	var old_parent: Node = node.get_parent()
	var old_index: int = node.get_index()
	var new_parent: Node = old_parent
	var parent_path: String = str(params.get("parent", "")).strip_edges()
	if parent_path != "":
		new_parent = _scene_service.find_node(parent_path)
		if new_parent == null:
			return {"status": "error", "error": "Parent not found: '%s'" % parent_path}

	var do_state: Dictionary = _capture_transform_state(node)
	var undo_state: Dictionary = _capture_transform_state(node)
	var changed: bool = false

	var position = params.get("position", null)
	if position is Array:
		var coerced_position = _coerce_position(node, position)
		if coerced_position != null:
			do_state["position"] = coerced_position
			changed = true

	var rotation = params.get("rotation", null)
	if rotation is Array:
		var coerced_rotation = _coerce_rotation(node, rotation)
		if coerced_rotation != null:
			do_state["rotation"] = coerced_rotation
			changed = true

	var scale = params.get("scale", null)
	if scale is Array:
		var coerced_scale = _coerce_scale(node, scale)
		if coerced_scale != null:
			do_state["scale"] = coerced_scale
			changed = true

	if new_parent != old_parent:
		changed = true

	if not changed:
		return {"status": "ok", "data": _scene_service.serialize_node(node)}

	_undo_service.move_node_action(
		"Move %s" % node.name,
		node,
		new_parent,
		new_parent.get_child_count() if new_parent != old_parent else old_index,
		old_parent,
		old_index,
		do_state,
		undo_state,
		root
	)
	return {"status": "ok", "data": _scene_service.serialize_node(node)}


func get_properties(params: Dictionary) -> Dictionary:
	var path: String = str(params.get("path", ""))
	var node: Node = _scene_service.find_node(path)
	if node == null:
		return {"status": "error", "error": "Node not found: '%s'" % path}
	return _scene_service.list_properties(node)


func set_property(params: Dictionary) -> Dictionary:
	var path: String = str(params.get("path", ""))
	var property_name: String = str(params.get("property", "")).strip_edges()
	var node: Node = _scene_service.find_node(path)
	if node == null:
		return {"status": "error", "error": "Node not found: '%s'" % path}
	if property_name == "":
		return {"status": "error", "error": "No property provided"}

	var property_info: Dictionary = _scene_service.get_property_info(node, property_name)
	if property_info.is_empty():
		return {"status": "error", "error": "Property not found: '%s'" % property_name}

	var do_value: Variant = _codec.coerce_value(property_info, params.get("value", null))
	var undo_value: Variant = node.get(property_name)
	_undo_service.set_property_action(
		"Set %s.%s" % [node.name, property_name],
		node,
		property_name,
		do_value,
		undo_value,
		_scene_service.get_edited_scene_root()
	)

	return {
		"status": "ok",
		"data": {
			"path": path,
			"property": property_name,
			"value": _codec.serialize_value(node.get(property_name)),
		}
	}


func set_properties(params: Dictionary) -> Dictionary:
	var path: String = str(params.get("path", ""))
	var properties: Variant = params.get("properties", {})
	var node: Node = _scene_service.find_node(path)
	if node == null:
		return {"status": "error", "error": "Node not found: '%s'" % path}
	if not properties is Dictionary:
		return {"status": "error", "error": "The 'properties' parameter must be a dictionary"}

	var changes: Array[Dictionary] = []
	var failed: Array[String] = []
	for property_name in properties:
		var info: Dictionary = _scene_service.get_property_info(node, str(property_name))
		if info.is_empty():
			failed.append(str(property_name))
			continue
		changes.append({
			"property": str(property_name),
			"do": _codec.coerce_value(info, properties[property_name]),
			"undo": node.get(str(property_name)),
		})

	if changes.size() > 0:
		_undo_service.set_properties_action(
			"Set properties on %s" % node.name,
			node,
			changes,
			_scene_service.get_edited_scene_root()
		)

	var applied: Array[String] = []
	for change in changes:
		applied.append(change["property"])

	return {"status": "ok", "data": {"set": applied, "failed": failed}}


func _capture_transform_state(node: Node) -> Dictionary:
	var state: Dictionary = {}
	if node is Node2D:
		var n2d: Node2D = node
		state["position"] = n2d.position
		state["rotation"] = n2d.rotation_degrees
		state["scale"] = n2d.scale
	elif node is Node3D:
		var n3d: Node3D = node
		state["position"] = n3d.position
		state["rotation"] = n3d.rotation_degrees
		state["scale"] = n3d.scale
	return state


func _coerce_position(node: Node, raw: Array) -> Variant:
	if node is Node2D and raw.size() >= 2:
		return Vector2(float(raw[0]), float(raw[1]))
	if node is Node3D and raw.size() >= 3:
		return Vector3(float(raw[0]), float(raw[1]), float(raw[2]))
	return null


func _coerce_rotation(node: Node, raw: Array) -> Variant:
	if node is Node2D and raw.size() >= 1:
		return float(raw[0])
	if node is Node3D and raw.size() >= 3:
		return Vector3(float(raw[0]), float(raw[1]), float(raw[2]))
	return null


func _coerce_scale(node: Node, raw: Array) -> Variant:
	if node is Node2D and raw.size() >= 2:
		return Vector2(float(raw[0]), float(raw[1]))
	if node is Node3D and raw.size() >= 3:
		return Vector3(float(raw[0]), float(raw[1]), float(raw[2]))
	return null


func _instantiate_type(type_name: String) -> Node:
	match type_name.to_lower():
		"node":
			return Node.new()
		"node2d":
			return Node2D.new()
		"node3d", "spatial":
			return Node3D.new()
		"characterbody2d":
			return CharacterBody2D.new()
		"characterbody3d":
			return CharacterBody3D.new()
		"rigidbody2d":
			return RigidBody2D.new()
		"rigidbody3d":
			return RigidBody3D.new()
		"camera2d":
			return Camera2D.new()
		"camera3d":
			return Camera3D.new()
		"sprite2d":
			return Sprite2D.new()
		"sprite3d":
			return Sprite3D.new()
		"collisionshape2d":
			return CollisionShape2D.new()
		"collisionshape3d":
			return CollisionShape3D.new()
		"area2d":
			return Area2D.new()
		"area3d":
			return Area3D.new()
		"audiostreamplayer":
			return AudioStreamPlayer.new()
		"light2d":
			return PointLight2D.new()
		"light3d":
			return DirectionalLight3D.new()
		"cube":
			var mesh_instance: MeshInstance3D = MeshInstance3D.new()
			mesh_instance.mesh = BoxMesh.new()
			return mesh_instance
		"meshinstance3d":
			return MeshInstance3D.new()
		_:
			if ClassDB.class_exists(type_name):
				var instance: Variant = ClassDB.instantiate(type_name)
				if instance is Node:
					return instance
	return null
