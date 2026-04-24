@tool
extends RefCounted


func get_console_logs(context: RefCounted, params: Dictionary) -> Dictionary:
	return context.console_service.get_console_logs(params)


func clear_console(context: RefCounted) -> Dictionary:
	return context.console_service.clear_console()
