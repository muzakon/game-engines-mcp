@tool
extends RefCounted


func serialize_value(value: Variant) -> Variant:
	match typeof(value):
		TYPE_NIL, TYPE_BOOL, TYPE_INT, TYPE_FLOAT, TYPE_STRING:
			return value
		TYPE_VECTOR2:
			return [value.x, value.y]
		TYPE_VECTOR3:
			return [value.x, value.y, value.z]
		TYPE_VECTOR4:
			return [value.x, value.y, value.z, value.w]
		TYPE_COLOR:
			return "#" + value.to_html()
		TYPE_NODE_PATH:
			return str(value)
		TYPE_ARRAY:
			var output: Array = []
			for item in value:
				output.append(serialize_value(item))
			return output
		TYPE_DICTIONARY:
			var output: Dictionary = {}
			for key in value:
				output[str(key)] = serialize_value(value[key])
			return output
		_:
			if value is Resource:
				var resource: Resource = value
				return {
					"type": resource.get_class(),
					"path": resource.resource_path,
				}
			if value is Node:
				var node: Node = value
				return {
					"type": node.get_class(),
					"name": node.name,
					"instanceId": node.get_instance_id(),
				}
			return str(value)


func coerce_value(property_info: Dictionary, value: Variant) -> Variant:
	var property_type: int = int(property_info.get("type", TYPE_NIL))
	match property_type:
		TYPE_BOOL:
			return bool(value)
		TYPE_INT:
			return int(value)
		TYPE_FLOAT:
			return float(value)
		TYPE_STRING:
			return str(value)
		TYPE_VECTOR2:
			if value is Array and value.size() >= 2:
				return Vector2(float(value[0]), float(value[1]))
		TYPE_VECTOR3:
			if value is Array and value.size() >= 3:
				return Vector3(float(value[0]), float(value[1]), float(value[2]))
		TYPE_VECTOR4:
			if value is Array and value.size() >= 4:
				return Vector4(float(value[0]), float(value[1]), float(value[2]), float(value[3]))
		TYPE_COLOR:
			if value is String:
				return Color.from_string(value, Color.WHITE)
		TYPE_NODE_PATH:
			return NodePath(str(value))
	return value
