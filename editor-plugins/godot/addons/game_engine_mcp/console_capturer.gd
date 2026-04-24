@tool
extends RefCounted

var _logs: Array[Dictionary] = []
var _max_entries: int = 1000
var _total_logged: int = 0


func _init() -> void:
	# Capture all engine log messages
	OS.print_error.connect(_on_error)
	OS.print_warning.connect(_on_warning)


func _on_error(msg: String) -> void:
	_add_log("error", msg)


func _on_warning(msg: String) -> void:
	_add_log("warning", msg)


func _add_log(level: String, message: String) -> void:
	_total_logged += 1
	_logs.append({
		"level": level,
		"message": message.strip_edges(),
		"index": _total_logged
	})
	while _logs.size() > _max_entries:
		_logs.pop_front()


func get_console_logs(params: Dictionary) -> Dictionary:
	var count: int = params.get("count", 50)
	var level: String = params.get("level", "")

	var filtered: Array[Dictionary] = []
	var start := maxi(_logs.size() - count, 0)

	for i in range(start, _logs.size()):
		var entry: Dictionary = _logs[i]
		if level != "" and entry.get("level", "") != level:
			continue
		filtered.append(entry)

	return {"status": "ok", "data": {"logs": filtered, "totalAvailable": _total_logged, "returned": filtered.size()}}


func clear_console() -> Dictionary:
	_logs.clear()
	_total_logged = 0
	return {"status": "ok", "data": {"cleared": true}}
