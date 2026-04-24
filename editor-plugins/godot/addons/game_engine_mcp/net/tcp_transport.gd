@tool
extends RefCounted

const ClientConnection = preload("client_connection.gd")

var _server: TCPServer
var _clients: Array = []
var _running: bool = false
var _host: String = "127.0.0.1"
var _port: int = 9879
var _last_error: String = ""


func start(host: String, port: int) -> bool:
	stop()

	_host = host
	_port = port
	_last_error = ""
	_server = TCPServer.new()
	var err: int = _server.listen(_port, _host)
	if err != OK:
		_last_error = "Failed to listen on %s:%d (error %d)" % [_host, _port, err]
		_server = null
		return false

	_running = true
	return true


func stop() -> void:
	_running = false
	for client in _clients:
		client.close_connection()
	_clients.clear()
	if _server != null:
		_server.stop()
		_server = null


func poll_messages() -> Array[Dictionary]:
	var events: Array[Dictionary] = []
	if not _running or _server == null:
		return events

	while _server.is_connection_available():
		var peer: StreamPeerTCP = _server.take_connection()
		_clients.append(ClientConnection.new(peer))
		events.append({"type": "client_connected"})

	var disconnected: Array[int] = []
	for i in range(_clients.size()):
		var client: RefCounted = _clients[i]
		var lines: Array[String] = client.poll_messages()
		if not client.is_peer_connected():
			disconnected.append(i)
			continue

		for line in lines:
			events.append({"type": "message", "client": client, "line": line})

	for i in range(disconnected.size() - 1, -1, -1):
		var index: int = disconnected[i]
		_clients[index].close_connection()
		_clients.remove_at(index)
		events.append({"type": "client_disconnected"})

	return events


func send_response(client: RefCounted, response_json: String) -> void:
	if client != null:
		client.send_line(response_json)


func is_running() -> bool:
	return _running


func get_client_count() -> int:
	return _clients.size()


func get_last_error() -> String:
	return _last_error
