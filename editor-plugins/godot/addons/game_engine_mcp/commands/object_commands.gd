@tool
extends RefCounted


func get_object(context: RefCounted, params: Dictionary) -> Dictionary:
	return context.node_service.get_object(params)


func create_object(context: RefCounted, params: Dictionary) -> Dictionary:
	return context.node_service.create_object(params)


func delete_object(context: RefCounted, params: Dictionary) -> Dictionary:
	return context.node_service.delete_object(params)


func move_object(context: RefCounted, params: Dictionary) -> Dictionary:
	return context.node_service.move_object(params)
