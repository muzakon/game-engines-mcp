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
		"close_scene":
			return _editor_commands.close_scene(context)
		"select_file":
			return _editor_commands.select_file(context, params)
		"edit_node":
			return _editor_commands.edit_node(context, params)
		"edit_resource":
			return _editor_commands.edit_resource(context, params)
		"edit_script":
			return _editor_commands.edit_script(context, params)
		"add_root_node":
			return _editor_commands.add_root_node(context, params)
		"get_current_path":
			return _editor_commands.get_current_path(context)
		"get_current_directory":
			return _editor_commands.get_current_directory(context)
		"get_open_scenes":
			return _editor_commands.get_open_scenes(context)
		"get_playing_scene":
			return _editor_commands.get_playing_scene(context)
		"get_unsaved_scenes":
			return _editor_commands.get_unsaved_scenes(context)
		"get_selected_paths":
			return _editor_commands.get_selected_paths(context)
		"set_current_feature_profile":
			return _editor_commands.set_current_feature_profile(context, params)
		"set_main_screen_editor":
			return _editor_commands.set_main_screen_editor(context, params)
		"get_editor_scale":
			return _editor_commands.get_editor_scale(context)
		"get_editor_settings":
			return _editor_commands.get_editor_settings(context, params)
		"get_editor_setting":
			return _editor_commands.get_editor_setting(context, params)
		"set_editor_setting":
			return _editor_commands.set_editor_setting(context, params)
		"get_editor_setting_list":
			return _editor_commands.get_editor_setting_list(context)
		"get_selection":
			return _editor_commands.get_selection(context)
		"selection_add_node":
			return _editor_commands.selection_add_node(context, params)
		"selection_remove_node":
			return _editor_commands.selection_remove_node(context, params)
		"selection_clear":
			return _editor_commands.selection_clear(context)
		"get_resource_filesystem":
			return _editor_commands.get_resource_filesystem(context)
		"get_resource_previewer":
			return _editor_commands.get_resource_previewer(context)
		"get_inspector":
			return _editor_commands.get_inspector(context)
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
