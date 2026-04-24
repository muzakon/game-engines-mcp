@tool
extends Node

var _tcp_server: TCPServer
var _clients: Array[StreamPeerTCP] = []
var _host: String = "127.0.0.1"
var _port: int = 9879
var _running: bool = false
var _console_capturer: ConsoleCapturer


func _ready() -> void:
	_console_capturer = ConsoleCapturer.new()


func start_server(host: String = "", port: int = 0) -> bool:
	if host != "":
		_host = host
	if port > 0:
		_port = port

	_tcp_server = TCPServer.new()
	var err := _tcp_server.listen(_port, _host)
	if err != OK:
		push_error("[GameEngineMCP] Failed to listen on %s:%d (error %d)" % [_host, _port, err])
		return false

	_running = true
	print("[GameEngineMCP] Listening on %s:%d" % [_host, _port])
	return true


func stop_server() -> void:
	_running = false
	for client in _clients:
		client.disconnect_from_host()
	_clients.clear()
	if _tcp_server:
		_tcp_server.stop()
		_tcp_server = null
	print("[GameEngineMCP] Stopped")


func is_running() -> bool:
	return _running


func get_client_count() -> int:
	return _clients.size()


func _process(_delta: float) -> void:
	if not _running or not _tcp_server:
		return

	# Accept new connections
	if _tcp_server.is_connection_available():
		var client := _tcp_server.take_connection()
		_clients.append(client)
		print("[GameEngineMCP] Client connected (%d total)" % _clients.size())

	# Process each client
	var to_remove: Array[int] = []
	for i in range(_clients.size()):
		var client: StreamPeerTCP = _clients[i]
		client.poll()

		if client.get_status() != StreamPeerTCP.STATUS_CONNECTED:
			to_remove.append(i)
			continue

		while client.get_available_bytes() > 0:
			var raw := client.get_utf8_string()
			if raw == "":
				continue
			# May contain multiple newline-delimited messages
			for line in raw.split("\n", false):
				var response := _handle_message(line.strip_edges())
				client.put_utf8_string(response + "\n")

	# Remove disconnected clients (reverse order)
	for i in to_remove:
		_clients[i].disconnect_from_host()
		_clients.remove_at(i)
	if to_remove.size() > 0:
		print("[GameEngineMCP] Client disconnected (%d remaining)" % _clients.size())


func _handle_message(json_str: String) -> String:
	var parsed := JSON.parse_string(json_str)
	if parsed == null or not parsed is Dictionary:
		return JSON.stringify({"id": 0, "status": "error", "error": "Invalid JSON"})

	var req: Dictionary = parsed
	var req_id: int = req.get("id", 0)
	var command: String = req.get("command", "")
	var params: Dictionary = req.get("params", {})

	var result: Dictionary = _route_command(command, params)
	result["id"] = req_id
	if not result.has("status"):
		result["status"] = "ok"

	return JSON.stringify(result)


func _route_command(command: String, params: Dictionary) -> Dictionary:
	match command:
		"ping":
			return Commands.ping()
		"get_editor_info":
			return Commands.get_editor_info()
		"play":
			return Commands.play()
		"pause":
			return Commands.pause()
		"stop":
			return Commands.stop()
		"get_console_logs":
			return _console_capturer.get_console_logs(params)
		"clear_console":
			return _console_capturer.clear_console()
		"get_scene_hierarchy":
			return Commands.get_scene_hierarchy()
		"get_active_scene":
			return Commands.get_active_scene()
		"save_scene":
			return Commands.save_scene(params)
		"get_object":
			return Commands.get_object(params)
		"create_object":
			return Commands.create_object(params)
		"delete_object":
			return Commands.delete_object(params)
		"move_object":
			return Commands.move_object(params)
		"get_properties":
			return Commands.get_properties(params)
		"set_property":
			return Commands.set_property(params)
		"set_properties":
			return Commands.set_properties(params)
		"list_assets":
			return Commands.list_assets(params)
		"take_screenshot":
			return Commands.take_screenshot()
		"execute_code":
			return Commands.execute_code(params)
		_:
			return {"status": "error", "error": "Unknown command: " + command}
