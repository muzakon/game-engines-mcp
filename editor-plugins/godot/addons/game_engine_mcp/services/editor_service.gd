@tool
extends RefCounted

var _editor_interface


func _init(editor_interface_instance) -> void:
	_editor_interface = editor_interface_instance


func ping() -> Dictionary:
	return {
		"status": "ok",
		"data": {
			"status": "alive",
			"engine": "godot",
			"version": Engine.get_version_info().string,
		}
	}


func get_editor_info() -> Dictionary:
	return {
		"status": "ok",
		"data": {
			"engine": "godot",
			"version": Engine.get_version_info().string,
			"platform": OS.get_name(),
			"projectName": ProjectSettings.get_setting("application/config/name", "Unknown"),
			"projectPath": ProjectSettings.globalize_path("res://"),
			"isPlaying": _editor_interface.is_playing_scene(),
		}
	}


func play() -> Dictionary:
	_editor_interface.play_main_scene()
	return {"status": "ok", "data": {"playing": true}}


func pause() -> Dictionary:
	return {
		"status": "error",
		"error": "Godot editor pause is not exposed by the public EditorInterface API."
	}


func stop() -> Dictionary:
	_editor_interface.stop_playing_scene()
	return {"status": "ok", "data": {"playing": false}}
