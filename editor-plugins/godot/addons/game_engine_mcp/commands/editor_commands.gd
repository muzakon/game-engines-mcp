@tool
extends RefCounted


func ping(context: RefCounted) -> Dictionary:
	return context.editor_service.ping()


func get_editor_info(context: RefCounted) -> Dictionary:
	return context.editor_service.get_editor_info()


func play(context: RefCounted) -> Dictionary:
	return context.editor_service.play()


func pause(context: RefCounted) -> Dictionary:
	return context.editor_service.pause()


func stop(context: RefCounted) -> Dictionary:
	return context.editor_service.stop()
