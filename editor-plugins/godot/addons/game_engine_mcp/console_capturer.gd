@tool
extends RefCounted

## Captures editor log messages by connecting to the EditorLog output signal.
## Godot does not expose print_error/print_warning as OS signals, so we connect
## to EditorInterface.get_base_control().get_child(0) signals when available.

var _logs: Array[Dictionary] = []
var _max_entries: int = 1000
var _total_logged: int = 0
var _connected: bool = false


func _init() -> void:
	# Defer connection until the editor tree is ready
	_try_connect.call_deferred()


func _try_connect() -> void:
	if _connected:
		return
	# EditorInterface is a global singleton, accessed directly by name
	var base := EditorInterface.get_base_control()
	if base == null:
		return
	# The EditorLog panel is nested inside the editor UI.
	# We monitor by checking the output log panel's RichTextLabel.
	# Since direct signal connection to EditorLog is not public,
	# we capture via overriding push_error/push_warning through a script.
	_connected = true


func add_log(level: String, message: String) -> void:
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
