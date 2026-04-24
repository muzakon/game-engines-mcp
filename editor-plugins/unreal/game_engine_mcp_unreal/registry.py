"""Central command registry."""

from __future__ import annotations

from typing import Any

from .commands import actors, assets, editor, properties, scene
from .commands import CommandHandler
from .protocol import make_ok

COMMANDS: dict[str, CommandHandler] = {
    "ping": editor.ping,
    "list_commands": lambda req_id, params: make_ok(
        req_id, {"commands": list_command_metadata()}
    ),
    "get_editor_info": editor.get_editor_info,
    "play": editor.play,
    "pause": editor.pause,
    "stop": editor.stop,
    "get_console_logs": editor.get_console_logs,
    "clear_console": editor.clear_console,
    "get_scene_hierarchy": scene.get_scene_hierarchy,
    "get_active_scene": scene.get_active_scene,
    "save_scene": scene.save_scene,
    "new_level": scene.new_level,
    "open_level": scene.open_level,
    "save_all_levels": scene.save_all_levels,
    "get_object": actors.get_object,
    "create_object": actors.create_object,
    "delete_object": actors.delete_object,
    "move_object": actors.move_object,
    "find_actors": actors.find_actors,
    "duplicate_actor": actors.duplicate_actor,
    "set_actor_visible": actors.set_actor_visible,
    "get_properties": properties.get_properties,
    "set_property": properties.set_property,
    "set_properties": properties.set_properties,
    "list_assets": assets.list_assets,
    "get_asset": assets.get_asset,
    "delete_asset": assets.delete_asset,
    "move_asset": assets.move_asset,
    "rename_asset": assets.rename_asset,
    "duplicate_asset": assets.duplicate_asset,
    "import_asset": assets.import_asset,
    "take_screenshot": editor.take_screenshot,
    "execute_code": editor.execute_code,
    "get_selection": editor.get_selection,
    "set_selection": editor.set_selection,
    "get_viewport_camera": editor.get_viewport_camera,
    "set_viewport_camera": editor.set_viewport_camera,
    "get_content_directory": assets.get_content_directory,
    "get_project_dir": assets.get_project_dir,
}

_PARAMS: dict[str, list[str]] = {
    "get_console_logs": ["count", "level"],
    "new_level": ["path"],
    "open_level": ["path"],
    "get_object": ["path"],
    "create_object": ["name", "type", "parent"],
    "delete_object": ["path"],
    "move_object": ["path", "position", "rotation", "scale", "parent"],
    "get_properties": ["path", "component"],
    "set_property": ["path", "component", "property", "value"],
    "set_properties": ["path", "component", "properties"],
    "find_actors": ["name", "class_type", "tag", "limit"],
    "list_assets": ["path", "recursive"],
    "get_asset": ["path"],
    "delete_asset": ["path"],
    "move_asset": ["source", "destination"],
    "rename_asset": ["path", "name"],
    "duplicate_asset": ["source", "destination"],
    "import_asset": ["path"],
    "execute_code": ["code", "language"],
    "set_selection": ["paths"],
    "set_viewport_camera": ["location", "rotation"],
    "get_content_directory": ["path"],
    "set_actor_visible": ["path", "visible"],
    "duplicate_actor": ["path", "name"],
}

_DESCRIPTIONS: dict[str, str] = {
    "ping": "Check that the UE editor plugin is alive.",
    "list_commands": "Return supported UE editor plugin commands.",
    "get_editor_info": "Return UE version, project paths, play state.",
    "play": "Enter play-in-editor mode.",
    "pause": "Toggle pause in editor.",
    "stop": "Exit play-in-editor mode.",
    "get_console_logs": "Return captured console logs.",
    "clear_console": "Clear captured console log buffer.",
    "get_scene_hierarchy": "Return the current level hierarchy.",
    "get_active_scene": "Return active level metadata.",
    "save_scene": "Save the current level.",
    "new_level": "Create a new level.",
    "open_level": "Open a level by asset path.",
    "save_all_levels": "Save all dirty levels.",
    "get_object": "Return actor details.",
    "create_object": "Spawn an actor.",
    "delete_object": "Destroy an actor.",
    "move_object": "Set transform on actor.",
    "get_properties": "Read component properties.",
    "set_property": "Set a property on a component.",
    "set_properties": "Batch-set properties.",
    "find_actors": "Search actors by name, class, or tag.",
    "list_assets": "List assets under a content path.",
    "get_asset": "Return asset metadata.",
    "delete_asset": "Delete an asset.",
    "move_asset": "Move an asset.",
    "rename_asset": "Rename an asset.",
    "duplicate_asset": "Duplicate an asset.",
    "import_asset": "Import/reimport an asset.",
    "take_screenshot": "Capture the viewport as a high-resolution screenshot.",
    "execute_code": "Execute Python code in the editor.",
    "get_selection": "Return selected actors.",
    "set_selection": "Select actors by name/path.",
    "get_viewport_camera": "Get the editor viewport camera info.",
    "set_viewport_camera": "Set the viewport camera.",
    "get_content_directory": "List content under a path.",
    "get_project_dir": "Return the project directory.",
    "set_actor_visible": "Set actor visibility.",
    "duplicate_actor": "Duplicate an actor.",
}


def list_command_metadata() -> list[dict[str, Any]]:
    metadata = []
    for name in COMMANDS:
        item: dict[str, Any] = {
            "name": name,
            "description": _DESCRIPTIONS.get(name, ""),
        }
        if name in _PARAMS:
            item["parameters"] = _PARAMS[name]
        metadata.append(item)
    return metadata
