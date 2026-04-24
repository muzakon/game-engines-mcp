@tool
extends RefCounted


static func parse_json(json_str: String) -> Dictionary:
	var parsed: Variant = JSON.parse_string(json_str)
	if parsed == null or not parsed is Dictionary:
		return {"ok": false, "error": "Invalid JSON"}

	var request: Dictionary = parsed
	var params: Variant = request.get("params", {})
	if not params is Dictionary:
		params = {}

	return {
		"ok": true,
		"request": {
			"id": int(request.get("id", 0)),
			"command": str(request.get("command", "")),
			"params": params,
		}
	}
