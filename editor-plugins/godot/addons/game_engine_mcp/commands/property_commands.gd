@tool
extends RefCounted


func get_properties(context: RefCounted, params: Dictionary) -> Dictionary:
	return context.node_service.get_properties(params)


func set_property(context: RefCounted, params: Dictionary) -> Dictionary:
	return context.node_service.set_property(params)


func set_properties(context: RefCounted, params: Dictionary) -> Dictionary:
	return context.node_service.set_properties(params)
