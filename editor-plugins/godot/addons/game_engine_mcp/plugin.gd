@tool
extends EditorPlugin

const McpServer = preload("mcp_server.gd")

var _server: Node


func _enter_tree() -> void:
	_server = McpServer.new()
	add_child(_server)
	_server.start_server()
	print("[GameEngineMCP] Plugin loaded")


func _exit_tree() -> void:
	if _server:
		_server.stop_server()
		_server.queue_free()
		_server = null
	print("[GameEngineMCP] Plugin unloaded")
