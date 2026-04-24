@tool
extends RefCounted

const ConsoleService = preload("services/console_service.gd")

var _service: RefCounted = ConsoleService.new()


func add_log(level: String, message: String) -> void:
	_service.add_log(level, message)


func get_console_logs(params: Dictionary) -> Dictionary:
	return _service.get_console_logs(params)


func clear_console() -> Dictionary:
	return _service.clear_console()
