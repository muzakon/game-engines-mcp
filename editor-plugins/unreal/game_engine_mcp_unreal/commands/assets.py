"""Content browser and asset commands."""

from __future__ import annotations

from typing import Any

from ..protocol import make_error, make_ok
from ..unreal_import import unreal


def list_assets(req_id: int, params: dict[str, Any]) -> str:
    path = _content_path(params.get("path", "/Game/"))
    recursive = bool(params.get("recursive", True))
    try:
        asset_registry = unreal.AssetRegistryHelpers.get_asset_registry()
        assets = asset_registry.get_assets_by_path(path, recursive=recursive)
        return make_ok(
            req_id,
            {"assets": [_asset_data(asset) for asset in assets], "count": len(assets)},
        )
    except Exception as exc:
        return make_error(req_id, f"Failed to list assets: {exc}")


def get_asset(req_id: int, params: dict[str, Any]) -> str:
    path = params.get("path", "")
    if not path:
        return make_error(req_id, "No path provided")
    try:
        asset = unreal.load_asset(path)
        if not asset:
            return make_error(req_id, f"Asset not found: '{path}'")
        return make_ok(
            req_id,
            {
                "name": asset.get_name(),
                "path": asset.get_path_name(),
                "type": asset.get_class().get_name(),
            },
        )
    except Exception as exc:
        return make_error(req_id, f"Failed to get asset: {exc}")


def delete_asset(req_id: int, params: dict[str, Any]) -> str:
    path = params.get("path", "")
    if not path:
        return make_error(req_id, "No path provided")
    try:
        return make_ok(
            req_id,
            {"deleted": unreal.EditorAssetLibrary.delete_asset(path), "path": path},
        )
    except Exception as exc:
        return make_error(req_id, f"Failed to delete asset: {exc}")


def move_asset(req_id: int, params: dict[str, Any]) -> str:
    source = params.get("source", params.get("from", ""))
    destination = params.get("destination", params.get("to", ""))
    if not source or not destination:
        return make_error(req_id, "Missing source or destination")
    try:
        result = unreal.EditorAssetLibrary.rename_asset(source, destination)
        return make_ok(
            req_id, {"moved": result, "source": source, "destination": destination}
        )
    except Exception as exc:
        return make_error(req_id, f"Failed to move asset: {exc}")


def rename_asset(req_id: int, params: dict[str, Any]) -> str:
    path = params.get("path", "")
    name = params.get("name", "")
    if not path or not name:
        return make_error(req_id, "Missing path or name")
    try:
        folder = path.rsplit("/", 1)[0]
        new_path = f"{folder}/{name}" if folder else name
        result = unreal.EditorAssetLibrary.rename_asset(path, new_path)
        return make_ok(req_id, {"renamed": result, "path": path, "newPath": new_path})
    except Exception as exc:
        return make_error(req_id, f"Failed to rename asset: {exc}")


def duplicate_asset(req_id: int, params: dict[str, Any]) -> str:
    source = params.get("source", params.get("from", ""))
    destination = params.get("destination", params.get("to", ""))
    if not source or not destination:
        return make_error(req_id, "Missing source or destination")
    try:
        result = unreal.EditorAssetLibrary.duplicate_asset(source, destination)
        return make_ok(
            req_id, {"duplicated": result, "source": source, "destination": destination}
        )
    except Exception as exc:
        return make_error(req_id, f"Failed to duplicate asset: {exc}")


def import_asset(req_id: int, params: dict[str, Any]) -> str:
    path = params.get("path", "")
    if not path:
        return make_error(req_id, "No path provided")
    try:
        if unreal.load_asset(path):
            unreal.EditorAssetLibrary.save_asset(path, only_if_is_dirty=False)
            return make_ok(req_id, {"reimported": True, "path": path})
        return make_error(req_id, f"Asset not found for import: '{path}'")
    except Exception as exc:
        return make_error(req_id, f"Failed to import asset: {exc}")


def get_content_directory(req_id: int, params: dict[str, Any]) -> str:
    path = _content_path(params.get("path", "/Game/"))
    try:
        asset_registry = unreal.AssetRegistryHelpers.get_asset_registry()
        assets = asset_registry.get_assets_by_path(path, recursive=False)
        return make_ok(
            req_id,
            {
                "path": path,
                "assets": [_asset_data(asset) for asset in assets],
                "count": len(assets),
            },
        )
    except Exception as exc:
        return make_error(req_id, f"Failed to list content: {exc}")


def get_project_dir(req_id: int, params: dict[str, Any]) -> str:
    try:
        return make_ok(
            req_id,
            {
                "projectDir": unreal.Paths.project_dir(),
                "contentDir": unreal.Paths.project_content_dir(),
                "configDir": unreal.Paths.project_config_dir(),
                "projectFilePath": unreal.Paths.get_project_file_path(),
            },
        )
    except Exception as exc:
        return make_error(req_id, f"Failed to get project dir: {exc}")


def _asset_data(asset_data: Any) -> dict[str, str]:
    return {
        "name": str(asset_data.asset_name),
        "path": str(asset_data.package_name),
        "type": str(asset_data.asset_class_path),
    }


def _content_path(path: str) -> str:
    if not path:
        return "/Game/"
    return path if path.startswith("/") else f"/Game/{path}"
