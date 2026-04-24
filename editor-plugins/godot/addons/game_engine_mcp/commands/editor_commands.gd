@tool
extends RefCounted


func ping(context: RefCounted) -> Dictionary:
	return context.editor_service.ping()


func get_editor_info(context: RefCounted) -> Dictionary:
	return context.editor_service.get_editor_info()


func play(context: RefCounted) -> Dictionary:
	return context.editor_service.play()


func play_current_scene(context: RefCounted) -> Dictionary:
	return context.editor_service.play_current_scene()


func pause(context: RefCounted) -> Dictionary:
	return context.editor_service.pause()


func stop(context: RefCounted) -> Dictionary:
	return context.editor_service.stop()


func open_scene(context: RefCounted, params: Dictionary) -> Dictionary:
	return context.editor_service.open_scene(str(params.get("path", "")), bool(params.get("inherited", false)))


func reload_scene(context: RefCounted, params: Dictionary) -> Dictionary:
	return context.editor_service.reload_scene(str(params.get("path", "")))


func save_scene_as(context: RefCounted, params: Dictionary) -> Dictionary:
	return context.editor_service.save_scene_as(str(params.get("path", "")), bool(params.get("with_preview", true)))


func mark_scene_as_unsaved(context: RefCounted) -> Dictionary:
	return context.editor_service.mark_scene_as_unsaved()


func get_open_scene_roots(context: RefCounted) -> Dictionary:
	return context.editor_service.get_open_scene_roots()


func get_editor_docks(context: RefCounted) -> Dictionary:
	return context.editor_service.get_editor_docks()


func close_scene(context: RefCounted) -> Dictionary:
	return context.editor_service.close_scene()


func select_file(context: RefCounted, params: Dictionary) -> Dictionary:
	return context.editor_service.select_file(str(params.get("file", "")))


func edit_node(context: RefCounted, params: Dictionary) -> Dictionary:
	return context.editor_service.edit_node(str(params.get("path", "")))


func edit_resource(context: RefCounted, params: Dictionary) -> Dictionary:
	return context.editor_service.edit_resource(str(params.get("path", "")))


func edit_script(context: RefCounted, params: Dictionary) -> Dictionary:
	return context.editor_service.edit_script(
		str(params.get("path", "")),
		int(params.get("line", -1)),
		int(params.get("column", 0)),
		bool(params.get("grab_focus", true))
	)


func add_root_node(context: RefCounted, params: Dictionary) -> Dictionary:
	return context.editor_service.add_root_node(str(params.get("path", "")))


func get_current_path(context: RefCounted) -> Dictionary:
	return context.editor_service.get_current_path()


func get_current_directory(context: RefCounted) -> Dictionary:
	return context.editor_service.get_current_directory()


func get_open_scenes(context: RefCounted) -> Dictionary:
	return context.editor_service.get_open_scenes()


func get_playing_scene(context: RefCounted) -> Dictionary:
	return context.editor_service.get_playing_scene()


func get_unsaved_scenes(context: RefCounted) -> Dictionary:
	return context.editor_service.get_unsaved_scenes()


func get_selected_paths(context: RefCounted) -> Dictionary:
	return context.editor_service.get_selected_paths()


func set_current_feature_profile(context: RefCounted, params: Dictionary) -> Dictionary:
	return context.editor_service.set_current_feature_profile(str(params.get("profile_name", "")))


func set_main_screen_editor(context: RefCounted, params: Dictionary) -> Dictionary:
	return context.editor_service.set_main_screen_editor(str(params.get("name", "")))


func get_editor_scale(context: RefCounted) -> Dictionary:
	return context.editor_service.get_editor_scale()


func get_editor_settings(context: RefCounted, params: Dictionary) -> Dictionary:
	return context.editor_service.get_editor_settings(params)


func get_editor_setting(context: RefCounted, params: Dictionary) -> Dictionary:
	return context.editor_service.get_editor_setting(str(params.get("key", "")))


func set_editor_setting(context: RefCounted, params: Dictionary) -> Dictionary:
	return context.editor_service.set_editor_setting(str(params.get("key", "")), params.get("value", null))


func get_editor_setting_list(context: RefCounted) -> Dictionary:
	return context.editor_service.get_editor_setting_list()


func get_selection(context: RefCounted) -> Dictionary:
	return context.editor_service.get_selection()


func selection_add_node(context: RefCounted, params: Dictionary) -> Dictionary:
	return context.editor_service.selection_add_node(str(params.get("path", "")))


func selection_remove_node(context: RefCounted, params: Dictionary) -> Dictionary:
	return context.editor_service.selection_remove_node(str(params.get("path", "")))


func selection_clear(context: RefCounted) -> Dictionary:
	return context.editor_service.selection_clear()


func get_resource_filesystem(context: RefCounted) -> Dictionary:
	return context.editor_service.get_resource_filesystem()


func get_resource_previewer(context: RefCounted) -> Dictionary:
	return context.editor_service.get_resource_previewer()


func get_inspector(context: RefCounted) -> Dictionary:
	return context.editor_service.get_inspector()


func play_custom_scene(context: RefCounted, params: Dictionary) -> Dictionary:
	return context.editor_service.play_custom_scene(str(params.get("path", "")))


func save_all_scenes(context: RefCounted) -> Dictionary:
	return context.editor_service.save_all_scenes()


func restart_editor(context: RefCounted, params: Dictionary) -> Dictionary:
	return context.editor_service.restart_editor(bool(params.get("save", true)))


func get_current_feature_profile(context: RefCounted) -> Dictionary:
	return context.editor_service.get_current_feature_profile()


func get_editor_paths(context: RefCounted) -> Dictionary:
	return context.editor_service.get_editor_paths()


func is_plugin_enabled(context: RefCounted, params: Dictionary) -> Dictionary:
	return context.editor_service.is_plugin_enabled(str(params.get("plugin", "")))


func set_plugin_enabled(context: RefCounted, params: Dictionary) -> Dictionary:
	return context.editor_service.set_plugin_enabled(str(params.get("plugin", "")), bool(params.get("enabled", true)))


func get_editor_theme(context: RefCounted) -> Dictionary:
	return context.editor_service.get_editor_theme()


func get_editor_language(context: RefCounted) -> Dictionary:
	return context.editor_service.get_editor_language()


func is_multi_window_enabled(context: RefCounted) -> Dictionary:
	return context.editor_service.is_multi_window_enabled()


func inspect_object(context: RefCounted, params: Dictionary) -> Dictionary:
	return context.editor_service.inspect_object(
		str(params.get("path", "")),
		str(params.get("for_property", "")),
		bool(params.get("inspector_only", false))
	)


func set_object_edited(context: RefCounted, params: Dictionary) -> Dictionary:
	return context.editor_service.set_object_edited(str(params.get("path", "")), bool(params.get("edited", true)))


func is_object_edited(context: RefCounted, params: Dictionary) -> Dictionary:
	return context.editor_service.is_object_edited(str(params.get("path", "")))


func get_snap_settings(context: RefCounted) -> Dictionary:
	return context.editor_service.get_snap_settings()


func push_toast(context: RefCounted, params: Dictionary) -> Dictionary:
	return context.editor_service.push_toast(str(params.get("message", "")), int(params.get("severity", 0)))


func navigate_filesystem(context: RefCounted, params: Dictionary) -> Dictionary:
	return context.editor_service.navigate_filesystem(str(params.get("path", "")))


func scan_filesystem(context: RefCounted) -> Dictionary:
	return context.editor_service.scan_filesystem()


func scan_sources(context: RefCounted) -> Dictionary:
	return context.editor_service.scan_sources()


func reimport_files(context: RefCounted, params: Dictionary) -> Dictionary:
	var files: Array = params.get("files", [])
	return context.editor_service.reimport_files(files)


func get_file_type(context: RefCounted, params: Dictionary) -> Dictionary:
	return context.editor_service.get_file_type(str(params.get("path", "")))


func get_filesystem_directory(context: RefCounted, params: Dictionary) -> Dictionary:
	return context.editor_service.get_filesystem_directory(str(params.get("path", "")))


func get_current_script(context: RefCounted) -> Dictionary:
	return context.editor_service.get_current_script()


func get_open_scripts(context: RefCounted) -> Dictionary:
	return context.editor_service.get_open_scripts()


func get_unsaved_script_files(context: RefCounted) -> Dictionary:
	return context.editor_service.get_unsaved_script_files()


func save_all_scripts(context: RefCounted) -> Dictionary:
	return context.editor_service.save_all_scripts()


func reload_open_files(context: RefCounted) -> Dictionary:
	return context.editor_service.reload_open_files()


func get_breakpoints(context: RefCounted) -> Dictionary:
	return context.editor_service.get_breakpoints()


func goto_line(context: RefCounted, params: Dictionary) -> Dictionary:
	return context.editor_service.goto_line(int(params.get("line", 0)))


func new_scene(context: RefCounted, params: Dictionary) -> Dictionary:
	return {
		"status": "error",
		"error": "Godot's public EditorInterface does not expose a direct new_scene API.",
		"data": {"requestedRootType": str(params.get("root_type", "Node"))}
	}
