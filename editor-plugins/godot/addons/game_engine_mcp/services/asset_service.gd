@tool
extends RefCounted


func list_assets(params: Dictionary) -> Dictionary:
	var path: String = str(params.get("path", "res://")).strip_edges()
	if path == "":
		path = "res://"

	var dir_access: DirAccess = DirAccess.open(path)
	if dir_access == null:
		return {"status": "error", "error": "Cannot open path: '%s'" % path}

	var assets: Array[Dictionary] = []
	dir_access.list_dir_begin()
	var file_name: String = dir_access.get_next()
	while file_name != "":
		if not file_name.begins_with("."):
			var full_path: String = path.path_join(file_name)
			var is_dir: bool = dir_access.current_is_dir()
			assets.append({
				"name": file_name,
				"path": full_path,
				"type": "directory" if is_dir else file_name.get_extension(),
			})
		file_name = dir_access.get_next()
	dir_access.list_dir_end()

	return {"status": "ok", "data": {"assets": assets, "count": assets.size(), "path": path}}
