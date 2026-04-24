"""Small Unreal API adapters shared by command handlers."""

from __future__ import annotations

from typing import Any

from .unreal_import import unreal

SHAPE_PATHS = {
    "cube": "/Engine/BasicShapes/Cube.Cube",
    "sphere": "/Engine/BasicShapes/Sphere.Sphere",
    "cylinder": "/Engine/BasicShapes/Cylinder.Cylinder",
    "cone": "/Engine/BasicShapes/Cone.Cone",
    "plane": "/Engine/BasicShapes/Plane.Plane",
}

ACTOR_SHORTCUTS = {
    "empty": ("Actor", None),
    "actor": ("Actor", None),
    "cube": ("StaticMeshActor", "cube"),
    "cubemesh": ("StaticMeshActor", "cube"),
    "sphere": ("StaticMeshActor", "sphere"),
    "cylinder": ("StaticMeshActor", "cylinder"),
    "cone": ("StaticMeshActor", "cone"),
    "plane": ("StaticMeshActor", "plane"),
    "floor": ("StaticMeshActor", "plane"),
    "pointlight": ("PointLight", None),
    "spotlight": ("SpotLight", None),
    "directionallight": ("DirectionalLight", None),
    "camera": ("CameraActor", None),
    "playerstart": ("PlayerStart", None),
    "skylight": ("SkyLight", None),
    "exponentialheightfog": ("ExponentialHeightFog", None),
}


def get_actor_by_path(path: str) -> Any | None:
    """Find an actor by full path, label, or leaf name."""
    if not path:
        return None

    for candidate in (path, path.rsplit("/", maxsplit=1)[-1].strip()):
        if not candidate:
            continue
        try:
            actor = unreal.EditorLevelLibrary.get_actor_reference(candidate)
            if actor:
                return actor
        except Exception:
            pass

    leaf = path.rsplit("/", maxsplit=1)[-1].strip()
    for actor in unreal.EditorLevelLibrary.get_all_level_actors():
        if actor.get_name() in (path, leaf):
            return actor
        try:
            if actor.get_actor_label() in (path, leaf):
                return actor
        except Exception:
            pass
    return None


def get_actor_path(actor: Any) -> str:
    parts: list[str] = []
    current = actor
    while current is not None:
        parts.append(current.get_name())
        current = current.get_attach_parent_actor()
    return "/".join(reversed(parts))


def serialize_actor(actor: Any, include_components: bool = True) -> dict[str, Any]:
    if actor is None:
        return {}

    result: dict[str, Any] = {
        "name": actor.get_name(),
        "type": actor.get_class().get_name(),
        "path": get_actor_path(actor),
        "active": True,
    }

    try:
        location = actor.get_actor_location()
        rotation = actor.get_actor_rotation()
        scale = actor.get_actor_scale3d()
        result["transform"] = {
            "location": [location.x, location.y, location.z],
            "rotation": [rotation.roll, rotation.pitch, rotation.yaw],
            "scale": [scale.x, scale.y, scale.z],
        }
    except Exception:
        pass

    if include_components:
        result["components"] = [
            {
                "name": component.get_name(),
                "type": component.get_class().get_name(),
                "properties": get_component_properties(component),
            }
            for component in safe_components(actor)
        ]

    return result


def safe_components(actor: Any) -> list[Any]:
    try:
        return list(actor.get_components_by_class(unreal.ActorComponent))
    except Exception:
        return []


def get_component_properties(component: Any) -> dict[str, Any]:
    properties: dict[str, Any] = {}
    try:
        property_names = component.get_editor_properties()
    except Exception:
        property_names = ("relative_location", "relative_rotation", "relative_scale3d")

    for prop in property_names:
        key = str(prop)
        try:
            properties[key] = serialize_value(component.get_editor_property(key))
        except Exception:
            pass
    return properties


def find_component(actor: Any, component_name: str) -> Any | None:
    if not component_name:
        return None
    normalized_name = component_name.lower()
    for component in safe_components(actor):
        if (
            component.get_name().lower() == normalized_name
            or component.get_class().get_name().lower() == normalized_name
        ):
            return component
    try:
        root = actor.get_root_component()
        if root and root.get_class().get_name().lower() == normalized_name:
            return root
    except Exception:
        pass
    return None


def serialize_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, unreal.Vector):
        return [value.x, value.y, value.z]
    if isinstance(value, unreal.Rotator):
        return [value.roll, value.pitch, value.yaw]
    if isinstance(value, unreal.LinearColor):
        return [value.r, value.g, value.b, value.a]
    if isinstance(value, (list, tuple)):
        return [serialize_value(item) for item in value]
    try:
        return str(value)
    except Exception:
        return f"<{type(value).__name__}>"


def coerce_property_value(prop_name: str, value: Any) -> Any:
    if isinstance(value, list) and len(value) == 3:
        normalized_name = prop_name.lower()
        if "location" in normalized_name or "scale" in normalized_name:
            return to_vector(value)
        if "rotation" in normalized_name or "rotator" in normalized_name:
            return to_rotator(value)
    return value


def to_vector(values: list[Any]) -> Any:
    return unreal.Vector(float(values[0]), float(values[1]), float(values[2]))


def to_rotator(values: list[Any]) -> Any:
    return unreal.Rotator(float(values[0]), float(values[1]), float(values[2]))
