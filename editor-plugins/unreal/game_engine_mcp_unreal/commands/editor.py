"""General editor, play-mode, console, code, and viewport commands."""

from __future__ import annotations

import traceback
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from typing import Any

from .. import log_buffer
from ..protocol import make_error, make_ok
from ..ue_helpers import serialize_actor, to_rotator, to_vector
from ..unreal_import import unreal


def ping(req_id: int, params: dict[str, Any]) -> str:
    version = unreal.SystemLibrary.get_engine_version()
    return make_ok(req_id, {"status": "alive", "engine": "unreal", "version": version})


def get_editor_info(req_id: int, params: dict[str, Any]) -> str:
    return make_ok(
        req_id,
        {
            "engine": "unreal",
            "version": unreal.SystemLibrary.get_engine_version(),
            "platform": str(unreal.SystemLibrary.get_platform_name()),
            "projectName": unreal.Paths.get_project_file_name(),
            "projectPath": unreal.Paths.project_dir(),
            "projectFilePath": unreal.Paths.get_project_file_path(),
            "contentDir": unreal.Paths.project_content_dir(),
            "isPlaying": is_playing(),
        },
    )


def play(req_id: int, params: dict[str, Any]) -> str:
    try:
        subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        if subsystem:
            subsystem.editor_play_simulate()
        else:
            unreal.EditorLevelLibrary.editor_play_simulate()
        return make_ok(req_id, {"playing": True})
    except Exception as exc:
        return make_error(req_id, f"Failed to start play mode: {exc}")


def pause(req_id: int, params: dict[str, Any]) -> str:
    try:
        unreal.SystemLibrary.execute_console_command(
            unreal.EditorLevelLibrary.get_editor_world(), "TogglePause"
        )
        return make_ok(req_id, {"paused": True})
    except Exception as exc:
        return make_error(req_id, f"Failed to toggle pause: {exc}")


def stop(req_id: int, params: dict[str, Any]) -> str:
    try:
        unreal.EditorLevelLibrary.editor_end_play()
        return make_ok(req_id, {"playing": False})
    except Exception as exc:
        return make_error(req_id, f"Failed to stop play mode: {exc}")


def get_console_logs(req_id: int, params: dict[str, Any]) -> str:
    count = int(params.get("count") or 50)
    return make_ok(req_id, {"logs": log_buffer.read_logs(count, params.get("level"))})


def clear_console(req_id: int, params: dict[str, Any]) -> str:
    log_buffer.clear_logs()
    return make_ok(req_id, {"cleared": True})


def execute_code(req_id: int, params: dict[str, Any]) -> str:
    code = params.get("code", "")
    language = params.get("language", "python")
    if not code:
        return make_error(req_id, "No code provided")
    if language.lower() not in ("python", "py"):
        return make_error(
            req_id,
            f"Unsupported language: '{language}'. Only Python is supported in UE.",
        )

    try:
        stdout_buffer = StringIO()
        stderr_buffer = StringIO()
        with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
            exec(code, {"unreal": unreal, "__builtins__": __builtins__})
        return make_ok(
            req_id,
            {"output": stdout_buffer.getvalue(), "error": stderr_buffer.getvalue()},
        )
    except Exception as exc:
        return make_error(
            req_id,
            f"Code execution failed: {exc}",
            {"output": "", "error": traceback.format_exc()},
        )


def take_screenshot(req_id: int, params: dict[str, Any]) -> str:
    try:
        world = unreal.EditorLevelLibrary.get_editor_world()
        unreal.SystemLibrary.execute_console_command(
            world, "HighResScreenshot 1920x1080"
        )
        return make_ok(
            req_id,
            {"message": "Screenshot triggered. Check project/Screenshots/ directory."},
        )
    except Exception as exc:
        return make_error(req_id, f"Screenshot failed: {exc}")


def get_selection(req_id: int, params: dict[str, Any]) -> str:
    try:
        actors = unreal.EditorLevelLibrary.get_selected_level_actors()
        serialized = [
            serialize_actor(actor, include_components=False) for actor in actors
        ]
        return make_ok(req_id, {"actors": serialized, "count": len(serialized)})
    except Exception as exc:
        return make_error(req_id, f"Failed to get selection: {exc}")


def set_selection(req_id: int, params: dict[str, Any]) -> str:
    from ..ue_helpers import get_actor_by_path

    paths = params.get("paths", [])
    if isinstance(paths, str):
        paths = [paths]

    try:
        unreal.EditorLevelLibrary.clear_actor_selection_set()
        selected = []
        for path in paths:
            actor = get_actor_by_path(path)
            if actor:
                unreal.EditorLevelLibrary.set_actor_selection_state(actor, True)
                selected.append(serialize_actor(actor, include_components=False))
        return make_ok(req_id, {"actors": selected, "count": len(selected)})
    except Exception as exc:
        return make_error(req_id, f"Failed to set selection: {exc}")


def get_viewport_camera(req_id: int, params: dict[str, Any]) -> str:
    try:
        result = unreal.EditorLevelLibrary.get_level_viewport_camera_info()
        if not result:
            return make_error(req_id, "Could not get viewport camera info")
        location, rotation = result
        return make_ok(
            req_id,
            {
                "location": [location.x, location.y, location.z],
                "rotation": [rotation.roll, rotation.pitch, rotation.yaw],
            },
        )
    except Exception as exc:
        return make_error(req_id, f"Failed to get viewport camera: {exc}")


def set_viewport_camera(req_id: int, params: dict[str, Any]) -> str:
    location = params.get("location")
    rotation = params.get("rotation")
    try:
        loc = to_vector(location) if location else unreal.Vector(0, 0, 0)
        rot = to_rotator(rotation) if rotation else unreal.Rotator(0, 0, 0)
        unreal.EditorLevelLibrary.set_level_viewport_camera_info(loc, rot)
        return make_ok(req_id, {"location": location, "rotation": rotation})
    except Exception as exc:
        return make_error(req_id, f"Failed to set viewport camera: {exc}")


def is_playing() -> bool:
    try:
        subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        if subsystem:
            return subsystem.is_play_in_editor_currently_running()
    except Exception:
        pass
    try:
        return len(unreal.EditorLevelLibrary.get_pie_worlds(False)) > 0
    except Exception:
        return False
