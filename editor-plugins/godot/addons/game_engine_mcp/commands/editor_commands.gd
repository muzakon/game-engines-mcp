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


func new_scene(context: RefCounted, params: Dictionary) -> Dictionary:
	return {
		"status": "error",
		"error": "Godot's public EditorInterface does not expose a direct new_scene API.",
		"data": {"requestedRootType": str(params.get("root_type", "Node"))}
	}
