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


func new_scene(context: RefCounted, params: Dictionary) -> Dictionary:
	return {
		"status": "error",
		"error": "Godot's public EditorInterface does not expose a direct new_scene API.",
		"data": {"requestedRootType": str(params.get("root_type", "Node"))}
	}
