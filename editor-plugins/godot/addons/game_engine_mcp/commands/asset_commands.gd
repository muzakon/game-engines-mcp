@tool
extends RefCounted


func list_assets(context: RefCounted, params: Dictionary) -> Dictionary:
	return context.asset_service.list_assets(params)
