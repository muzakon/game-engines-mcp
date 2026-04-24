@tool
extends RefCounted

var peer: StreamPeerTCP
var buffer: String = ""


func _init(tcp_peer: StreamPeerTCP) -> void:
	peer = tcp_peer


func is_peer_connected() -> bool:
	return peer != null and peer.get_status() == StreamPeerTCP.STATUS_CONNECTED


func poll_messages() -> Array[String]:
	var messages: Array[String] = []
	if peer == null:
		return messages

	peer.poll()
	if not is_peer_connected():
		return messages

	var available: int = peer.get_available_bytes()
	if available <= 0:
		return messages

	buffer += peer.get_utf8_string(available)
	while true:
		var newline: int = buffer.find("\n")
		if newline < 0:
			break

		var line: String = buffer.substr(0, newline).strip_edges()
		buffer = buffer.substr(newline + 1)
		if line != "":
			messages.append(line)

	return messages


func send_line(line: String) -> void:
	if is_peer_connected():
		peer.put_data((line + "\n").to_utf8_buffer())


func close_connection() -> void:
	if peer != null:
		peer.disconnect_from_host()
