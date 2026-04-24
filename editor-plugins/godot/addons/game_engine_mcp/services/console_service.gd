@tool
extends RefCounted

var _logs: Array[Dictionary] = []
var _max_entries: int = 500
var _total_logged: int = 0


func _init(max_entries: int = 500) -> void:
	_max_entries = clampi(max_entries, 50, 5000)
	add_log(
		"info",
		"Godot does not expose an editor-wide console stream to plugins. Only Game Engine MCP internal logs are recorded."
	)


func set_max_entries(value: int) -> void:
	_max_entries = clampi(value, 50, 5000)
	while _logs.size() > _max_entries:
		_logs.pop_front()


func add_log(level: String, message: String, source: String = "game_engine_mcp") -> void:
	_total_logged += 1
	_logs.append({
		"level": level,
		"message": message.strip_edges(),
		"source": source,
		"index": _total_logged,
	})
	while _logs.size() > _max_entries:
		_logs.pop_front()


func info(message: String, source: String = "game_engine_mcp") -> void:
	add_log("info", message, source)


func warning(message: String, source: String = "game_engine_mcp") -> void:
	add_log("warning", message, source)


func error(message: String, source: String = "game_engine_mcp") -> void:
	add_log("error", message, source)


func get_console_logs(params: Dictionary) -> Dictionary:
	var count: int = clampi(int(params.get("count", 50)), 1, _max_entries)
	var level: String = str(params.get("level", "")).to_lower()
	var filtered: Array[Dictionary] = []
	var start: int = maxi(_logs.size() - count, 0)

	for i in range(start, _logs.size()):
		var entry: Dictionary = _logs[i]
		if level != "" and str(entry.get("level", "")).to_lower() != level:
			continue
		filtered.append(entry)

	return {
		"status": "ok",
		"data": {
			"logs": filtered,
			"totalAvailable": _total_logged,
			"returned": filtered.size(),
			"capture": "limited",
			"message": "Only Game Engine MCP internal logs are available in Godot.",
		}
	}


func clear_console() -> Dictionary:
	_logs.clear()
	_total_logged = 0
	add_log(
		"info",
		"Console buffer cleared. Only Game Engine MCP internal logs are recorded."
	)
	return {"status": "ok", "data": {"cleared": true}}
