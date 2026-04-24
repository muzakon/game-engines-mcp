"""Level and hierarchy commands."""

from __future__ import annotations

from typing import Any

from ..protocol import make_error, make_ok
from ..unreal_import import unreal


def get_scene_hierarchy(req_id: int, params: dict[str, Any]) -> str:
    try:
        return make_ok(
            req_id, _build_hierarchy(unreal.EditorLevelLibrary.get_all_level_actors())
        )
    except Exception as exc:
        return make_error(req_id, f"Failed to get hierarchy: {exc}")


def get_active_scene(req_id: int, params: dict[str, Any]) -> str:
    try:
        world = unreal.EditorLevelLibrary.get_editor_world()
        if not world:
            return make_error(req_id, "No active level")
        actors = unreal.EditorLevelLibrary.get_all_level_actors()
        return make_ok(
            req_id,
            {
                "name": world.get_name(),
                "path": world.get_path_name(),
                "actorCount": len(actors),
            },
        )
    except Exception as exc:
        return make_error(req_id, f"Failed to get active scene: {exc}")


def save_scene(req_id: int, params: dict[str, Any]) -> str:
    try:
        return make_ok(
            req_id, {"saved": unreal.EditorLevelLibrary.save_current_level()}
        )
    except Exception as exc:
        return make_error(req_id, f"Failed to save level: {exc}")


def new_level(req_id: int, params: dict[str, Any]) -> str:
    path = _content_path(params.get("path", ""))
    if not path:
        return make_error(req_id, "No path provided")
    try:
        return make_ok(
            req_id, {"created": unreal.EditorLevelLibrary.new_level(path), "path": path}
        )
    except Exception as exc:
        return make_error(req_id, f"Failed to create level: {exc}")


def open_level(req_id: int, params: dict[str, Any]) -> str:
    path = _content_path(params.get("path", ""))
    if not path:
        return make_error(req_id, "No path provided")
    try:
        return make_ok(
            req_id, {"loaded": unreal.EditorLevelLibrary.load_level(path), "path": path}
        )
    except Exception as exc:
        return make_error(req_id, f"Failed to open level: {exc}")


def save_all_levels(req_id: int, params: dict[str, Any]) -> str:
    try:
        return make_ok(
            req_id, {"saved": unreal.EditorLevelLibrary.save_all_dirty_levels()}
        )
    except Exception as exc:
        return make_error(req_id, f"Failed to save levels: {exc}")


def _build_hierarchy(actors: list[Any]) -> dict[str, Any]:
    actor_map: dict[str, dict[str, Any]] = {}
    roots: list[dict[str, Any]] = []

    for actor in actors:
        name = actor.get_name()
        actor_map[name] = {
            "name": name,
            "type": actor.get_class().get_name(),
            "children": [],
        }

    for actor in actors:
        parent = actor.get_attach_parent_actor()
        node = actor_map[actor.get_name()]
        if parent is not None and parent.get_name() in actor_map:
            actor_map[parent.get_name()]["children"].append(node)
        else:
            roots.append(node)

    return {"name": "Root", "type": "Level", "children": roots}


def _content_path(path: str) -> str:
    if not path:
        return ""
    return path if path.startswith("/") else f"/Game/{path}"
