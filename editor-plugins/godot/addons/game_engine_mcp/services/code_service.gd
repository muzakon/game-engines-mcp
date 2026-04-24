@tool
extends RefCounted


func execute_code(params: Dictionary) -> Dictionary:
	var code: String = str(params.get("code", "")).strip_edges()
	if code == "":
		return {"status": "error", "error": "No code provided"}

	var expression: Expression = Expression.new()
	var err: int = expression.parse(code)
	if err != OK:
		return {
			"status": "ok",
			"data": {
				"error": "Parse error: " + expression.get_error_text(),
				"language": "gdscript",
			}
		}

	var result: Variant = expression.execute()
	if expression.has_execute_failed():
		return {
			"status": "ok",
			"data": {
				"error": expression.get_error_text(),
				"language": "gdscript",
			}
		}

	return {
		"status": "ok",
		"data": {
			"output": str(result) if result != null else "(null)",
			"language": "gdscript",
		}
	}
