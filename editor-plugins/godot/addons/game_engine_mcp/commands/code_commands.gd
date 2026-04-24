@tool
extends RefCounted


func execute_code(context: RefCounted, params: Dictionary) -> Dictionary:
	return context.code_service.execute_code(params)
