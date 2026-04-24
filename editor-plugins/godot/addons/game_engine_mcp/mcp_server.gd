@tool
extends Node

const McpSettings = preload("core/mcp_settings.gd")
const McpRequest = preload("core/mcp_request.gd")
const McpResponse = preload("core/mcp_response.gd")
const CommandContext = preload("core/command_context.gd")
const TcpTransport = preload("net/tcp_transport.gd")
const CommandRouter = preload("routing/command_router.gd")
const ConsoleService = preload("services/console_service.gd")
const PropertyCodec = preload("services/property_codec.gd")
const UndoService = preload("services/undo_service.gd")
const EditorService = preload("services/editor_service.gd")
const SceneService = preload("services/scene_service.gd")
const NodeService = preload("services/node_service.gd")
const AssetService = preload("services/asset_service.gd")
const ScreenshotService = preload("services/screenshot_service.gd")
const CodeService = preload("services/code_service.gd")

signal state_changed

var _settings: RefCounted
var _transport: RefCounted
var _router: RefCounted
var _context: RefCounted
var _last_error: String = ""
var _last_client_count: int = 0


func _ready() -> void:
	set_process(true)
	_settings = McpSettings.load_or_default()
	_build_context()
	if _settings.auto_start:
		start_server()
	else:
		emit_signal("state_changed")


func _process(_delta: float) -> void:
	if _transport == null or not _transport.is_running():
		return

	var events: Array[Dictionary] = _transport.poll_messages()
	for event in events:
		match event.get("type", ""):
			"client_connected":
				_context.console_service.info("Client connected")
			"client_disconnected":
				_context.console_service.info("Client disconnected")
			"message":
				var response_json: String = _handle_message(str(event.get("line", "")))
				_transport.send_response(event.get("client"), response_json)

	var current_client_count: int = _transport.get_client_count()
	if current_client_count != _last_client_count:
		_last_client_count = current_client_count
		emit_signal("state_changed")


func start_server(host: String = "", port: int = 0) -> bool:
	if host != "":
		_settings.host = host
	if port > 0:
		_settings.port = port
	_settings.normalize()

	if _transport.start(_settings.host, _settings.port):
		_last_error = ""
		_last_client_count = _transport.get_client_count()
		_context.console_service.info("Listening on %s:%d" % [_settings.host, _settings.port])
		emit_signal("state_changed")
		return true

	_last_error = _transport.get_last_error()
	_context.console_service.error(_last_error)
	emit_signal("state_changed")
	return false


func stop_server() -> void:
	if _transport != null and _transport.is_running():
		_transport.stop()
		_context.console_service.info("Server stopped")
	_last_client_count = 0
	emit_signal("state_changed")


func restart_server() -> bool:
	stop_server()
	return start_server()


func is_running() -> bool:
	return _transport != null and _transport.is_running()


func get_client_count() -> int:
	return _transport.get_client_count() if _transport != null else 0


func apply_settings(host: String, port: int, auto_start: bool, max_log_entries: int) -> Dictionary:
	var previous_host: String = _settings.host
	var previous_port: int = _settings.port
	_settings.host = host
	_settings.port = port
	_settings.auto_start = auto_start
	_settings.max_log_entries = max_log_entries
	_settings.normalize()
	var save_err: int = _settings.save()
	_context.console_service.set_max_entries(_settings.max_log_entries)

	var should_restart: bool = is_running() and (_settings.host != previous_host or _settings.port != previous_port)
	if should_restart:
		restart_server()
	else:
		emit_signal("state_changed")

	return {
		"saved": save_err == OK,
		"error": "" if save_err == OK else "Failed to save settings (error %d)" % save_err,
	}


func get_status_snapshot() -> Dictionary:
	return {
		"running": is_running(),
		"clientCount": get_client_count(),
		"host": _settings.host if _settings != null else "127.0.0.1",
		"port": _settings.port if _settings != null else 9879,
		"autoStart": _settings.auto_start if _settings != null else true,
		"maxLogEntries": _settings.max_log_entries if _settings != null else 500,
		"lastError": _last_error,
	}


func _build_context() -> void:
	_transport = TcpTransport.new()
	_router = CommandRouter.new()

	var codec: RefCounted = PropertyCodec.new()
	var console_service: RefCounted = ConsoleService.new(_settings.max_log_entries)
	var scene_service: RefCounted = SceneService.new(EditorInterface, codec)

	_context = CommandContext.new()
	_context.settings = _settings
	_context.console_service = console_service
	_context.editor_service = EditorService.new(EditorInterface)
	_context.scene_service = scene_service
	_context.node_service = NodeService.new(
		scene_service,
		UndoService.new(EditorInterface),
		codec
	)
	_context.asset_service = AssetService.new()
	_context.screenshot_service = ScreenshotService.new(EditorInterface)
	_context.code_service = CodeService.new()


func _handle_message(json_str: String) -> String:
	var parsed: Dictionary = McpRequest.parse_json(json_str)
	if not parsed.get("ok", false):
		return McpResponse.to_json(McpResponse.err(0, str(parsed.get("error", "Invalid JSON"))))

	var request: Dictionary = parsed["request"]
	var req_id := int(request.get("id", 0))
	var response: Dictionary = _router.route(request, _context)
	response["id"] = req_id
	if not response.has("status"):
		response["status"] = "ok"
	return McpResponse.to_json(response)
