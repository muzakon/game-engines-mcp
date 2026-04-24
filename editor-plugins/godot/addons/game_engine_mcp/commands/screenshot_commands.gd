@tool
extends RefCounted


func take_screenshot(context: RefCounted) -> Dictionary:
	return context.screenshot_service.take_screenshot()
