@tool
extends RefCounted

var _editor_interface


func _init(editor_interface_instance) -> void:
	_editor_interface = editor_interface_instance


func create_node_action(action_name: String, parent: Node, node: Node, owner: Node) -> void:
	var undo_redo = _editor_interface.get_editor_undo_redo()
	undo_redo.create_action(action_name, 0, owner)
	undo_redo.add_do_method(self, "_insert_node", parent, node, parent.get_child_count(), owner)
	undo_redo.add_do_reference(node)
	undo_redo.add_undo_method(self, "_detach_node", node)
	undo_redo.commit_action()


func delete_node_action(action_name: String, node: Node) -> void:
	var parent: Node = node.get_parent()
	var owner: Node = node.owner
	var index: int = node.get_index()
	var undo_redo = _editor_interface.get_editor_undo_redo()
	undo_redo.create_action(action_name, 0, owner if owner != null else parent)
	undo_redo.add_do_method(self, "_detach_node", node)
	undo_redo.add_undo_method(self, "_insert_node", parent, node, index, owner)
	undo_redo.add_undo_reference(node)
	undo_redo.commit_action()


func move_node_action(action_name: String, node: Node, new_parent: Node, new_index: int, old_parent: Node, old_index: int, do_state: Dictionary, undo_state: Dictionary, owner: Node) -> void:
	var undo_redo = _editor_interface.get_editor_undo_redo()
	undo_redo.create_action(action_name, 0, owner if owner != null else old_parent)

	if old_parent != new_parent or old_index != new_index:
		undo_redo.add_do_method(self, "_reparent_node", node, new_parent, new_index, owner)
		undo_redo.add_undo_method(self, "_reparent_node", node, old_parent, old_index, owner)

	undo_redo.add_do_method(self, "_apply_transform_state", node, do_state)
	undo_redo.add_undo_method(self, "_apply_transform_state", node, undo_state)
	undo_redo.commit_action()


func set_property_action(action_name: String, node: Node, property_name: String, do_value: Variant, undo_value: Variant, owner: Node) -> void:
	var undo_redo = _editor_interface.get_editor_undo_redo()
	undo_redo.create_action(action_name, 0, owner if owner != null else node)
	undo_redo.add_do_method(self, "_set_node_property", node, property_name, do_value)
	undo_redo.add_undo_method(self, "_set_node_property", node, property_name, undo_value)
	undo_redo.commit_action()


func set_properties_action(action_name: String, node: Node, changes: Array[Dictionary], owner: Node) -> void:
	var undo_redo = _editor_interface.get_editor_undo_redo()
	undo_redo.create_action(action_name, 0, owner if owner != null else node)
	for change in changes:
		undo_redo.add_do_method(self, "_set_node_property", node, change["property"], change["do"])
		undo_redo.add_undo_method(self, "_set_node_property", node, change["property"], change["undo"])
	undo_redo.commit_action()


func _insert_node(parent: Node, node: Node, index: int, owner: Node) -> void:
	if parent == null or node == null:
		return

	if node.get_parent() != null and node.get_parent() != parent:
		node.get_parent().remove_child(node)
	if node.get_parent() == null:
		parent.add_child(node)

	if parent.get_child_count() > 0:
		parent.move_child(node, clampi(index, 0, parent.get_child_count() - 1))

	if owner != null:
		_set_owner_recursive(node, owner)


func _detach_node(node: Node) -> void:
	if node == null:
		return
	var parent: Node = node.get_parent()
	if parent != null:
		parent.remove_child(node)


func _reparent_node(node: Node, new_parent: Node, index: int, owner: Node) -> void:
	if node == null or new_parent == null:
		return
	var current_parent: Node = node.get_parent()
	if current_parent != null and current_parent != new_parent:
		current_parent.remove_child(node)
	if node.get_parent() == null:
		new_parent.add_child(node)
	if new_parent.get_child_count() > 0:
		new_parent.move_child(node, clampi(index, 0, new_parent.get_child_count() - 1))
	if owner != null:
		_set_owner_recursive(node, owner)


func _set_node_property(node: Node, property_name: String, value: Variant) -> void:
	if node != null:
		node.set(property_name, value)


func _apply_transform_state(node: Node, state: Dictionary) -> void:
	if node == null:
		return

	if state.has("position"):
		var position = state["position"]
		if node is Node2D:
			(node as Node2D).position = position
		elif node is Node3D:
			(node as Node3D).position = position

	if state.has("rotation"):
		var rotation = state["rotation"]
		if node is Node2D:
			(node as Node2D).rotation_degrees = rotation
		elif node is Node3D:
			(node as Node3D).rotation_degrees = rotation

	if state.has("scale"):
		var scale = state["scale"]
		if node is Node2D:
			(node as Node2D).scale = scale
		elif node is Node3D:
			(node as Node3D).scale = scale


func _set_owner_recursive(node: Node, owner: Node) -> void:
	node.owner = owner
	for child in node.get_children():
		if child is Node:
			_set_owner_recursive(child, owner)
