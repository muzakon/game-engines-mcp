"""Actor and component property commands."""

from __future__ import annotations

from typing import Any

from ..protocol import make_error, make_ok
from ..ue_helpers import (
    coerce_property_value,
    find_component,
    get_actor_by_path,
    get_component_properties,
    safe_components,
    serialize_value,
)


def get_properties(req_id: int, params: dict[str, Any]) -> str:
    path = params.get("path", "")
    actor = get_actor_by_path(path)
    if not path:
        return make_error(req_id, "No path provided")
    if not actor:
        return make_error(req_id, f"Actor not found: '{path}'")

    try:
        component_name = params.get("component")
        components = (
            [find_component(actor, component_name)]
            if component_name
            else safe_components(actor)
        )
        properties = {
            component.get_name(): {
                "type": component.get_class().get_name(),
                "properties": get_component_properties(component),
            }
            for component in components
            if component is not None
        }
        return make_ok(req_id, {"path": path, "properties": properties})
    except Exception as exc:
        return make_error(req_id, f"Failed to get properties: {exc}")


def set_property(req_id: int, params: dict[str, Any]) -> str:
    path = params.get("path", "")
    prop_name = params.get("property", "")
    actor = get_actor_by_path(path)
    if not path or not prop_name:
        return make_error(req_id, "Missing path or property")
    if not actor:
        return make_error(req_id, f"Actor not found: '{path}'")

    component_name = params.get("component", "")
    target, error = _resolve_target(actor, path, component_name)
    if error:
        return make_error(req_id, error)

    try:
        value = coerce_property_value(prop_name, params.get("value"))
        target.set_editor_property(prop_name, value)
        return make_ok(
            req_id,
            {
                "path": path,
                "component": component_name,
                "property": prop_name,
                "value": serialize_value(value),
            },
        )
    except Exception as exc:
        return make_error(req_id, f"Failed to set property: {exc}")


def set_properties(req_id: int, params: dict[str, Any]) -> str:
    path = params.get("path", "")
    properties = params.get("properties", {})
    actor = get_actor_by_path(path)
    if not path or not properties:
        return make_error(req_id, "Missing path or properties")
    if not actor:
        return make_error(req_id, f"Actor not found: '{path}'")

    component_name = params.get("component", "")
    target, error = _resolve_target(actor, path, component_name)
    if error:
        return make_error(req_id, error)

    try:
        updated: dict[str, Any] = {}
        for prop_name, raw_value in properties.items():
            value = coerce_property_value(prop_name, raw_value)
            target.set_editor_property(prop_name, value)
            updated[prop_name] = serialize_value(value)
        return make_ok(
            req_id, {"path": path, "component": component_name, "updated": updated}
        )
    except Exception as exc:
        return make_error(req_id, f"Failed to set properties: {exc}")


def _resolve_target(
    actor: Any, actor_path: str, component_name: str
) -> tuple[Any, str | None]:
    if not component_name:
        return actor, None
    component = find_component(actor, component_name)
    if component is None:
        return actor, f"Component '{component_name}' not found on '{actor_path}'"
    return component, None
