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


func close_scene() -> Dictionary:
	var err: Error = _editor_interface.close_scene()
	if err != OK:
		return {"status": "error", "error": "Failed to close scene (error %d)" % err}
	return {"status": "ok", "data": {"closed": true}}


func select_file(file: String) -> Dictionary:
	if file.strip_edges() == "":
		return {"status": "error", "error": "No file path provided"}
	_editor_interface.select_file(file)
	return {"status": "ok", "data": {"selectedFile": file}}


func edit_node(path: String) -> Dictionary:
	var node: Node = _resolve_node(path)
	if node == null:
		return {"status": "error", "error": "Node not found: %s" % path}
	_editor_interface.edit_node(node)
	return {"status": "ok", "data": {"editedNode": path}}


func edit_resource(path: String) -> Dictionary:
	if path.strip_edges() == "":
		return {"status": "error", "error": "No resource path provided"}
	var resource: Resource = load(path)
	if resource == null:
		return {"status": "error", "error": "Resource not found: %s" % path}
	_editor_interface.edit_resource(resource)
	return {"status": "ok", "data": {"editedResource": path}}


func edit_script(path: String, line: int = -1, column: int = 0, grab_focus: bool = true) -> Dictionary:
	if path.strip_edges() == "":
		return {"status": "error", "error": "No script path provided"}
	var script: Script = load(path)
	if script == null:
		return {"status": "error", "error": "Script not found: %s" % path}
	_editor_interface.edit_script(script, line, column, grab_focus)
	return {"status": "ok", "data": {"editedScript": path, "line": line, "column": column}}


func add_root_node(path: String) -> Dictionary:
	var node: Node = _resolve_node(path)
	if node == null:
		return {"status": "error", "error": "Node not found: %s" % path}
	_editor_interface.add_root_node(node)
	return {"status": "ok", "data": {"rootNode": path}}


func get_current_path() -> Dictionary:
	return {"status": "ok", "data": {"currentPath": _editor_interface.get_current_path()}}


func get_current_directory() -> Dictionary:
	return {"status": "ok", "data": {"currentDirectory": _editor_interface.get_current_directory()}}


func get_open_scenes() -> Dictionary:
	var scenes: PackedStringArray = _editor_interface.get_open_scenes()
	return {"status": "ok", "data": {"openScenes": Array(scenes)}}


func get_playing_scene() -> Dictionary:
	return {"status": "ok", "data": {"playingScene": _editor_interface.get_playing_scene()}}


func get_unsaved_scenes() -> Dictionary:
	var scenes: PackedStringArray = _editor_interface.get_unsaved_scenes()
	return {"status": "ok", "data": {"unsavedScenes": Array(scenes)}}


func get_selected_paths() -> Dictionary:
	var paths: PackedStringArray = _editor_interface.get_selected_paths()
	return {"status": "ok", "data": {"selectedPaths": Array(paths)}}


func set_current_feature_profile(profile_name: String) -> Dictionary:
	_editor_interface.set_current_feature_profile(profile_name)
	return {"status": "ok", "data": {"profileName": profile_name}}


func set_main_screen_editor(name: String) -> Dictionary:
	_editor_interface.set_main_screen_editor(name)
	return {"status": "ok", "data": {"mainScreen": name}}


func get_editor_scale() -> Dictionary:
	return {"status": "ok", "data": {"editorScale": _editor_interface.get_editor_scale()}}


func get_editor_settings(params: Dictionary) -> Dictionary:
	var settings: EditorSettings = _editor_interface.get_editor_settings()
	var key: String = str(params.get("key", "")).strip_edges()
	if key != "":
		return {"status": "ok", "data": {"key": key, "value": settings.get_setting(key)}}
	var keys: Array = settings.get_property_list()
	return {"status": "ok", "data": {"properties": keys}}


func set_editor_setting(key: String, value: Variant) -> Dictionary:
	key = key.strip_edges()
	if key == "":
		return {"status": "error", "error": "No setting key provided"}
	var settings: EditorSettings = _editor_interface.get_editor_settings()
	settings.set_setting(key, value)
	return {"status": "ok", "data": {"key": key, "value": value}}


func get_editor_setting(key: String) -> Dictionary:
	key = key.strip_edges()
	if key == "":
		return {"status": "error", "error": "No setting key provided"}
	var settings: EditorSettings = _editor_interface.get_editor_settings()
	return {"status": "ok", "data": {"key": key, "value": settings.get_setting(key)}}


func get_editor_setting_list() -> Dictionary:
	var settings: EditorSettings = _editor_interface.get_editor_settings()
	var list: Array = settings.get_property_list()
	return {"status": "ok", "data": {"properties": list, "count": list.size()}}


func get_selection() -> Dictionary:
	var selection = _editor_interface.get_selection()
	var nodes: Array = selection.get_selected_nodes()
	var serialized: Array[Dictionary] = []
	for item in nodes:
		if item is Node:
			serialized.append({"name": item.name, "path": _node_path(item)})
	return {"status": "ok", "data": {"selectedNodes": serialized, "count": serialized.size()}}


func selection_add_node(path: String) -> Dictionary:
	var node: Node = _resolve_node(path)
	if node == null:
		return {"status": "error", "error": "Node not found: %s" % path}
	_editor_interface.get_selection().add_node(node)
	return {"status": "ok", "data": {"added": path}}


func selection_remove_node(path: String) -> Dictionary:
	var node: Node = _resolve_node(path)
	if node == null:
		return {"status": "error", "error": "Node not found: %s" % path}
	_editor_interface.get_selection().remove_node(node)
	return {"status": "ok", "data": {"removed": path}}


func selection_clear() -> Dictionary:
	_editor_interface.get_selection().clear()
	return {"status": "ok", "data": {"cleared": true}}


func get_resource_filesystem() -> Dictionary:
	var fs = _editor_interface.get_resource_filesystem()
	return {"status": "ok", "data": {"class": fs.get_class(), "isScanning": fs.is_scanning(), "progress": fs.get_scanning_progress()}}


func get_resource_previewer() -> Dictionary:
	var previewer = _editor_interface.get_resource_previewer()
	return {"status": "ok", "data": {"class": previewer.get_class()}}


func get_inspector() -> Dictionary:
	var inspector = _editor_interface.get_inspector()
	return {"status": "ok", "data": {"class": inspector.get_class(), "selectedPath": inspector.get_selected_path()}}


func play_custom_scene(path: String) -> Dictionary:
	if path.strip_edges() == "":
		return {"status": "error", "error": "No scene path provided"}
	_editor_interface.play_custom_scene(path)
	return {"status": "ok", "data": {"playing": true, "scene": path}}


func save_all_scenes() -> Dictionary:
	_editor_interface.save_all_scenes()
	return {"status": "ok", "data": {"savedAll": true}}


func restart_editor(save: bool = true) -> Dictionary:
	_editor_interface.restart_editor(save)
	return {"status": "ok", "data": {"restarting": true, "saved": save}}


func get_current_feature_profile() -> Dictionary:
	return {"status": "ok", "data": {"profileName": _editor_interface.get_current_feature_profile()}}


func get_editor_paths() -> Dictionary:
	var paths = _editor_interface.get_editor_paths()
	return {
		"status": "ok",
		"data": {
			"cacheDir": paths.get_cache_dir(),
			"configDir": paths.get_config_dir(),
			"dataDir": paths.get_data_dir(),
			"projectSettingsDir": paths.get_project_settings_dir(),
			"isSelfContained": paths.is_self_contained(),
			"selfContainedFile": paths.get_self_contained_file(),
		}
	}


func is_plugin_enabled(plugin: String) -> Dictionary:
	if plugin.strip_edges() == "":
		return {"status": "error", "error": "No plugin name provided"}
	return {"status": "ok", "data": {"plugin": plugin, "enabled": _editor_interface.is_plugin_enabled(plugin)}}


func set_plugin_enabled(plugin: String, enabled: bool) -> Dictionary:
	if plugin.strip_edges() == "":
		return {"status": "error", "error": "No plugin name provided"}
	_editor_interface.set_plugin_enabled(plugin, enabled)
	return {"status": "ok", "data": {"plugin": plugin, "enabled": enabled}}


func get_editor_theme() -> Dictionary:
	var theme: Theme = _editor_interface.get_editor_theme()
	return {"status": "ok", "data": {"class": theme.get_class(), "typeVariationCount": theme.get_type_variation_list("").size()}}


func get_editor_language() -> Dictionary:
	return {"status": "ok", "data": {"language": _editor_interface.get_editor_language()}}


func is_multi_window_enabled() -> Dictionary:
	return {"status": "ok", "data": {"multiWindowEnabled": _editor_interface.is_multi_window_enabled()}}


func inspect_object(path: String, for_property: String = "", inspector_only: bool = false) -> Dictionary:
	var node: Node = _resolve_node(path)
	if node == null:
		return {"status": "error", "error": "Node not found: %s" % path}
	_editor_interface.inspect_object(node, for_property, inspector_only)
	return {"status": "ok", "data": {"inspected": path, "forProperty": for_property}}


func set_object_edited(path: String, edited: bool) -> Dictionary:
	var node: Node = _resolve_node(path)
	if node == null:
		return {"status": "error", "error": "Node not found: %s" % path}
	_editor_interface.set_object_edited(node, edited)
	return {"status": "ok", "data": {"path": path, "edited": edited}}


func is_object_edited(path: String) -> Dictionary:
	var node: Node = _resolve_node(path)
	if node == null:
		return {"status": "error", "error": "Node not found: %s" % path}
	return {"status": "ok", "data": {"path": path, "edited": _editor_interface.is_object_edited(node)}}


func get_snap_settings() -> Dictionary:
	return {
		"status": "ok",
		"data": {
			"node3dTranslateSnap": _editor_interface.get_node_3d_translate_snap(),
			"node3dRotateSnap": _editor_interface.get_node_3d_rotate_snap(),
			"node3dScaleSnap": _editor_interface.get_node_3d_scale_snap(),
			"node3dSnapEnabled": _editor_interface.is_node_3d_snap_enabled(),
		}
	}


func push_toast(message: String, severity: int = 0) -> Dictionary:
	if message.strip_edges() == "":
		return {"status": "error", "error": "No message provided"}
	var toaster = _editor_interface.get_editor_toaster()
	toaster.push_toast(message, severity)
	return {"status": "ok", "data": {"message": message, "severity": severity}}


func navigate_filesystem(path: String) -> Dictionary:
	if path.strip_edges() == "":
		return {"status": "error", "error": "No path provided"}
	var dock = _editor_interface.get_file_system_dock()
	dock.navigate_to_path(path)
	return {"status": "ok", "data": {"navigatedTo": path}}


func scan_filesystem() -> Dictionary:
	var fs = _editor_interface.get_resource_filesystem()
	fs.scan()
	return {"status": "ok", "data": {"scanning": true}}


func scan_sources() -> Dictionary:
	var fs = _editor_interface.get_resource_filesystem()
	fs.scan_sources()
	return {"status": "ok", "data": {"scanningSources": true}}


func reimport_files(files: Array) -> Dictionary:
	if files.is_empty():
		return {"status": "error", "error": "No files provided"}
	var packed: PackedStringArray = PackedStringArray()
	for f in files:
		packed.append(str(f))
	var fs = _editor_interface.get_resource_filesystem()
	fs.reimport_files(packed)
	return {"status": "ok", "data": {"reimported": files}}


func get_file_type(path: String) -> Dictionary:
	if path.strip_edges() == "":
		return {"status": "error", "error": "No path provided"}
	var fs = _editor_interface.get_resource_filesystem()
	return {"status": "ok", "data": {"path": path, "type": fs.get_file_type(path)}}


func get_filesystem_directory(path: String) -> Dictionary:
	var fs = _editor_interface.get_resource_filesystem()
	var dir = fs.get_filesystem_path(path) if path.strip_edges() != "" else fs.get_filesystem()
	if dir == null:
		return {"status": "error", "error": "Directory not found: %s" % path}
	return {"status": "ok", "data": _serialize_fs_dir(dir)}


func get_current_script() -> Dictionary:
	var script_editor = _editor_interface.get_script_editor()
	var script = script_editor.get_current_script()
	if script == null:
		return {"status": "ok", "data": {"script": null, "path": ""}}
	return {"status": "ok", "data": {"script": script.get_class(), "path": script.resource_path}}


func get_open_scripts() -> Dictionary:
	var script_editor = _editor_interface.get_script_editor()
	var scripts: Array = script_editor.get_open_scripts()
	var result: Array[Dictionary] = []
	for s in scripts:
		result.append({"class": s.get_class(), "path": s.resource_path})
	return {"status": "ok", "data": {"scripts": result, "count": result.size()}}


func get_unsaved_script_files() -> Dictionary:
	var script_editor = _editor_interface.get_script_editor()
	var unsaved: PackedStringArray = script_editor.get_unsaved_files()
	return {"status": "ok", "data": {"unsavedFiles": Array(unsaved)}}


func save_all_scripts() -> Dictionary:
	var script_editor = _editor_interface.get_script_editor()
	script_editor.save_all_scripts()
	return {"status": "ok", "data": {"savedAll": true}}


func reload_open_files() -> Dictionary:
	var script_editor = _editor_interface.get_script_editor()
	script_editor.reload_open_files()
	return {"status": "ok", "data": {"reloaded": true}}


func get_breakpoints() -> Dictionary:
	var script_editor = _editor_interface.get_script_editor()
	var breakpoints: PackedStringArray = script_editor.get_breakpoints()
	return {"status": "ok", "data": {"breakpoints": Array(breakpoints)}}


func goto_line(line_number: int) -> Dictionary:
	var script_editor = _editor_interface.get_script_editor()
	script_editor.goto_line(line_number)
	return {"status": "ok", "data": {"line": line_number}}


func _serialize_fs_dir(dir) -> Dictionary:
	var result: Dictionary = {
		"name": dir.get_name(),
		"path": dir.get_path(),
		"fileCount": dir.get_file_count(),
		"subdirCount": dir.get_subdir_count(),
	}
	var files: Array[Dictionary] = []
	for i in range(dir.get_file_count()):
		files.append({
			"name": dir.get_file(i),
			"path": dir.get_file_path(i),
			"type": dir.get_file_type(i),
			"importValid": dir.get_file_import_is_valid(i),
		})
	result["files"] = files
	var subdirs: Array[Dictionary] = []
	for i in range(dir.get_subdir_count()):
		subdirs.append(_serialize_fs_dir(dir.get_subdir(i)))
	result["subdirs"] = subdirs
	return result


func _resolve_node(path: String) -> Node:
	return _editor_interface.get_edited_scene_root().get_node_or_null(path) if _editor_interface.get_edited_scene_root() != null else null


func _node_path(node: Node) -> String:
	var root: Node = _editor_interface.get_edited_scene_root()
	if root == null:
		return str(node.name)
	if root == node:
		return root.name
	return "%s/%s" % [root.name, str(root.get_path_to(node))]
