@tool
extends RefCounted

var _editor_interface


func _init(editor_interface_instance) -> void:
	_editor_interface = editor_interface_instance


func ping() -> Dictionary:
	return {
		"status": "ok",
		"data": {
			"status": "alive",
			"engine": "godot",
			"version": Engine.get_version_info().string,
		}
	}


func get_editor_info() -> Dictionary:
	return {
		"status": "ok",
		"data": {
			"engine": "godot",
			"version": Engine.get_version_info().string,
			"platform": OS.get_name(),
			"projectName": ProjectSettings.get_setting("application/config/name", "Unknown"),
			"projectPath": ProjectSettings.globalize_path("res://"),
			"isPlaying": _editor_interface.is_playing_scene(),
		}
	}


func play() -> Dictionary:
	_editor_interface.play_main_scene()
	return {"status": "ok", "data": {"playing": true}}


func play_current_scene() -> Dictionary:
	_editor_interface.play_current_scene()
	return {"status": "ok", "data": {"playing": true, "mode": "current_scene"}}


func pause() -> Dictionary:
	return {
		"status": "error",
		"error": "Godot editor pause is not exposed by the public EditorInterface API."
	}


func stop() -> Dictionary:
	_editor_interface.stop_playing_scene()
	return {"status": "ok", "data": {"playing": false}}


func open_scene(path: String, inherited: bool = false) -> Dictionary:
	if path.strip_edges() == "":
		return {"status": "error", "error": "No scene path provided"}
	_editor_interface.open_scene_from_path(path, inherited)
	return {"status": "ok", "data": {"opened": path, "inherited": inherited}}


func reload_scene(path: String) -> Dictionary:
	if path.strip_edges() == "":
		return {"status": "error", "error": "No scene path provided"}
	_editor_interface.reload_scene_from_path(path)
	return {"status": "ok", "data": {"reloaded": path}}


func save_scene_as(path: String, with_preview: bool = true) -> Dictionary:
	if path.strip_edges() == "":
		return {"status": "error", "error": "No target path provided"}
	_editor_interface.save_scene_as(path, with_preview)
	return {"status": "ok", "data": {"savedTo": path, "withPreview": with_preview}}


func mark_scene_as_unsaved() -> Dictionary:
	_editor_interface.mark_scene_as_unsaved()
	return {"status": "ok", "data": {"markedUnsaved": true}}


func get_open_scene_roots() -> Dictionary:
	var roots: Array = _editor_interface.get_open_scene_roots()
	var serialized: Array[Dictionary] = []
	for root in roots:
		if root is Node:
			var node: Node = root
			serialized.append({
				"name": node.name,
				"type": node.get_class(),
				"instanceId": node.get_instance_id(),
				"path": node.scene_file_path,
			})
	return {"status": "ok", "data": {"roots": serialized, "count": serialized.size()}}


func get_editor_docks() -> Dictionary:
	var base_control: Control = _editor_interface.get_base_control()
	var file_system_dock = _editor_interface.get_file_system_dock()
	var script_editor = _editor_interface.get_script_editor()
	return {
		"status": "ok",
		"data": {
			"baseControlClass": base_control.get_class() if base_control != null else "",
			"fileSystemDockClass": file_system_dock.get_class() if file_system_dock != null else "",
			"scriptEditorClass": script_editor.get_class() if script_editor != null else "",
		}
	}
