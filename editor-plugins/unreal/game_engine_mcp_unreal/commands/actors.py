"""Actor lookup, creation, transform, and visibility commands."""

from __future__ import annotations

from typing import Any

from ..protocol import make_error, make_ok
from ..ue_helpers import (
    ACTOR_SHORTCUTS,
    SHAPE_PATHS,
    get_actor_by_path,
    serialize_actor,
    to_rotator,
    to_vector,
)
from ..unreal_import import unreal


def get_object(req_id: int, params: dict[str, Any]) -> str:
    actor, error = _require_actor(params.get("path", ""))
    if error:
        return make_error(req_id, error)
    return make_ok(req_id, serialize_actor(actor))


def create_object(req_id: int, params: dict[str, Any]) -> str:
    name = params.get("name", "NewActor")
    obj_type = params.get("type", "Empty")
    parent_path = params.get("parent")

    try:
        class_name, mesh_key = ACTOR_SHORTCUTS.get(obj_type.lower(), (obj_type, None))
        actor_class = _resolve_actor_class(class_name)
        actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
            actor_class, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0)
        )
        if actor is None:
            return make_error(req_id, f"Failed to spawn actor of type '{class_name}'")

        _set_actor_label(actor, name)
        _assign_shortcut_mesh(actor, mesh_key)
        _attach_to_parent(actor, parent_path)
        return make_ok(req_id, serialize_actor(actor, include_components=False))
    except Exception as exc:
        return make_error(req_id, f"Failed to create actor: {exc}")


def delete_object(req_id: int, params: dict[str, Any]) -> str:
    path = params.get("path", "")
    actor, error = _require_actor(path)
    if error:
        return make_error(req_id, error)
    try:
        return make_ok(
            req_id,
            {"deleted": unreal.EditorLevelLibrary.destroy_actor(actor), "path": path},
        )
    except Exception as exc:
        return make_error(req_id, f"Failed to delete actor: {exc}")


def move_object(req_id: int, params: dict[str, Any]) -> str:
    actor, error = _require_actor(params.get("path", ""))
    if error:
        return make_error(req_id, error)

    try:
        position = params.get("position")
        rotation = params.get("rotation")
        scale = params.get("scale")
        if position and len(position) >= 3:
            actor.set_actor_location(to_vector(position), False, False)
        if rotation and len(rotation) >= 3:
            actor.set_actor_rotation(to_rotator(rotation), False)
        if scale and len(scale) >= 3:
            actor.set_actor_scale3d(to_vector(scale))
        _attach_to_parent(actor, params.get("parent"))
        return make_ok(req_id, serialize_actor(actor, include_components=False))
    except Exception as exc:
        return make_error(req_id, f"Failed to move actor: {exc}")


def find_actors(req_id: int, params: dict[str, Any]) -> str:
    name = params.get("name")
    class_type = params.get("class_type")
    tag = params.get("tag")
    limit = int(params.get("limit", 100))

    try:
        results = []
        for actor in unreal.EditorLevelLibrary.get_all_level_actors():
            if name and name.lower() not in actor.get_name().lower():
                continue
            if (
                class_type
                and class_type.lower() not in actor.get_class().get_name().lower()
            ):
                continue
            if tag and not _has_tag(actor, tag):
                continue
            results.append(serialize_actor(actor, include_components=False))
            if len(results) >= limit:
                break
        return make_ok(req_id, {"actors": results, "count": len(results)})
    except Exception as exc:
        return make_error(req_id, f"Failed to find actors: {exc}")


def duplicate_actor(req_id: int, params: dict[str, Any]) -> str:
    actor, error = _require_actor(params.get("path", ""))
    if error:
        return make_error(req_id, error)
    try:
        new_actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
            actor.get_class(), actor.get_actor_location(), actor.get_actor_rotation()
        )
        if params.get("name"):
            _set_actor_label(new_actor, params["name"])
        return make_ok(req_id, serialize_actor(new_actor, include_components=False))
    except Exception as exc:
        return make_error(req_id, f"Failed to duplicate actor: {exc}")


def set_actor_visible(req_id: int, params: dict[str, Any]) -> str:
    path = params.get("path", "")
    actor, error = _require_actor(path)
    if error:
        return make_error(req_id, error)
    visible = bool(params.get("visible", True))
    try:
        actor.set_actor_hidden_in_game(not visible)
        return make_ok(req_id, {"path": path, "visible": visible})
    except Exception as exc:
        return make_error(req_id, f"Failed to set visibility: {exc}")


def _resolve_actor_class(class_name: str) -> Any:
    try:
        actor_class = unreal.load_class(None, class_name)
        if actor_class:
            return actor_class
    except Exception:
        pass

    candidates = (
        unreal.Actor,
        unreal.StaticMeshActor,
        unreal.PointLight,
        unreal.SpotLight,
        unreal.DirectionalLight,
        unreal.CameraActor,
        unreal.PlayerStart,
        unreal.SkyLight,
        unreal.ExponentialHeightFog,
    )
    for candidate in candidates:
        if candidate.get_name().lower() == class_name.lower():
            return candidate
    return unreal.Actor


def _assign_shortcut_mesh(actor: Any, mesh_key: str | None) -> None:
    if not mesh_key or not isinstance(actor, unreal.StaticMeshActor):
        return
    mesh_path = SHAPE_PATHS.get(mesh_key)
    if not mesh_path:
        return
    mesh = unreal.load_asset(mesh_path)
    if mesh and actor.static_mesh_component:
        actor.static_mesh_component.set_static_mesh(mesh)


def _attach_to_parent(actor: Any, parent_path: str | None) -> None:
    if not parent_path:
        return
    parent = get_actor_by_path(parent_path)
    if parent:
        actor.attach_to_actor(
            parent,
            "",
            unreal.AttachmentRule.KEEP_WORLD,
            unreal.AttachmentRule.KEEP_WORLD,
            unreal.AttachmentRule.KEEP_WORLD,
            False,
        )


def _set_actor_label(actor: Any, name: str) -> None:
    try:
        actor.set_actor_label(name)
    except Exception:
        pass


def _has_tag(actor: Any, tag: str) -> bool:
    try:
        return tag in actor.tags
    except Exception:
        return False


def _require_actor(path: str) -> tuple[Any | None, str | None]:
    if not path:
        return None, "No path provided"
    actor = get_actor_by_path(path)
    if not actor:
        return None, f"Actor not found: '{path}'"
    return actor, None
