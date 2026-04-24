@tool
extends RefCounted

const EditorCommands = preload("../commands/editor_commands.gd")
const SceneCommands = preload("../commands/scene_commands.gd")
const ObjectCommands = preload("../commands/object_commands.gd")
const PropertyCommands = preload("../commands/property_commands.gd")
const AssetCommands = preload("../commands/asset_commands.gd")
const ScreenshotCommands = preload("../commands/screenshot_commands.gd")
const ConsoleCommands = preload("../commands/console_commands.gd")
const CodeCommands = preload("../commands/code_commands.gd")

var _editor_commands: RefCounted = EditorCommands.new()
var _scene_commands: RefCounted = SceneCommands.new()
var _object_commands: RefCounted = ObjectCommands.new()
var _property_commands: RefCounted = PropertyCommands.new()
var _asset_commands: RefCounted = AssetCommands.new()
var _screenshot_commands: RefCounted = ScreenshotCommands.new()
var _console_commands: RefCounted = ConsoleCommands.new()
var _code_commands: RefCounted = CodeCommands.new()


func route(request: Dictionary, context: RefCounted) -> Dictionary:
	var command: String = str(request.get("command", ""))
	var params: Dictionary = request.get("params", {})

	match command:
		"ping":
			return _editor_commands.ping(context)
		"get_editor_info":
			return _editor_commands.get_editor_info(context)
		"play":
			return _editor_commands.play(context)
		"play_current_scene":
			return _editor_commands.play_current_scene(context)
		"pause":
			return _editor_commands.pause(context)
		"stop":
			return _editor_commands.stop(context)
		"open_scene":
			return _editor_commands.open_scene(context, params)
		"new_scene":
			return _editor_commands.new_scene(context, params)
		"reload_scene":
			return _editor_commands.reload_scene(context, params)
		"save_scene_as":
			return _editor_commands.save_scene_as(context, params)
		"mark_scene_as_unsaved":
			return _editor_commands.mark_scene_as_unsaved(context)
		"get_open_scene_roots":
			return _editor_commands.get_open_scene_roots(context)
		"get_editor_docks":
			return _editor_commands.get_editor_docks(context)
		"get_console_logs":
			return _console_commands.get_console_logs(context, params)
		"clear_console":
			return _console_commands.clear_console(context)
		"get_scene_hierarchy":
			return _scene_commands.get_scene_hierarchy(context)
		"get_active_scene":
			return _scene_commands.get_active_scene(context)
		"save_scene":
			return _scene_commands.save_scene(context, params)
		"get_object":
			return _object_commands.get_object(context, params)
		"create_object":
			return _object_commands.create_object(context, params)
		"delete_object":
			return _object_commands.delete_object(context, params)
		"move_object":
			return _object_commands.move_object(context, params)
		"get_properties":
			return _property_commands.get_properties(context, params)
		"set_property":
			return _property_commands.set_property(context, params)
		"set_properties":
			return _property_commands.set_properties(context, params)
		"list_assets":
			return _asset_commands.list_assets(context, params)
		"take_screenshot":
			return _screenshot_commands.take_screenshot(context)
		"execute_code":
			return _code_commands.execute_code(context, params)
		_:
			return {"status": "error", "error": "Unknown command: " + command}
