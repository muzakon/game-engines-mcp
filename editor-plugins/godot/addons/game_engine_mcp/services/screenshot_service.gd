@tool
extends RefCounted

var _editor_interface


func _init(editor_interface_instance) -> void:
	_editor_interface = editor_interface_instance


func take_screenshot() -> Dictionary:
	var viewport: SubViewport = null
	for i in range(4):
		var candidate: SubViewport = _editor_interface.get_editor_viewport_3d(i)
		if candidate != null:
			viewport = candidate
			break

	if viewport == null:
		viewport = _editor_interface.get_editor_viewport_2d()
	if viewport == null:
		return {"status": "error", "error": "No viewport available"}

	var image: Image = viewport.get_texture().get_image()
	if image == null:
		return {"status": "error", "error": "Failed to capture viewport"}

	var png_data: PackedByteArray = image.save_png_to_buffer()
	return {
		"status": "ok",
		"data": {
			"image_base64": Marshalls.raw_to_base64(png_data),
			"width": image.get_width(),
			"height": image.get_height(),
			"format": "png",
		}
	}
