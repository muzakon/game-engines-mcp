@tool
extends RefCounted


static func ok(id: int, data: Variant = null) -> Dictionary:
	var response: Dictionary = {"id": id, "status": "ok"}
	if data != null:
		response["data"] = data
	return response


static func err(id: int, message: String, data: Variant = null) -> Dictionary:
	var response: Dictionary = {"id": id, "status": "error", "error": message}
	if data != null:
		response["data"] = data
	return response


static func to_json(response: Dictionary) -> String:
	return JSON.stringify(response)
