@tool
extends RefCounted


func get_scene_hierarchy(context: RefCounted) -> Dictionary:
	return context.scene_service.get_scene_hierarchy()


func get_active_scene(context: RefCounted) -> Dictionary:
	return context.scene_service.get_active_scene()


func save_scene(context: RefCounted, params: Dictionary) -> Dictionary:
	return context.scene_service.save_scene(params)
