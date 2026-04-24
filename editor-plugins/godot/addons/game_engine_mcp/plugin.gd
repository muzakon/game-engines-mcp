@tool
extends EditorPlugin

const McpServer = preload("mcp_server.gd")
const StatusDock = preload("ui/status_dock.gd")

var _server: Node
var _dock: Control
var _refresh_accumulator: float = 0.0


func _enter_tree() -> void:
	_server = McpServer.new()
	add_child(_server)
	_dock = StatusDock.new()
	_dock.start_requested.connect(_on_start_requested)
	_dock.stop_requested.connect(_on_stop_requested)
	_dock.restart_requested.connect(_on_restart_requested)
	_dock.settings_applied.connect(_on_settings_applied)
	add_control_to_dock(DOCK_SLOT_RIGHT_BL, _dock)
	_server.state_changed.connect(_refresh_dock_status)
	_sync_dock_settings()
	_refresh_dock_status()
	set_process(true)


func _exit_tree() -> void:
	set_process(false)
	if _dock:
		remove_control_from_docks(_dock)
		_dock.queue_free()
		_dock = null
	if _server:
		_server.stop_server()
		_server.queue_free()
		_server = null


func _process(delta: float) -> void:
	_refresh_accumulator += delta
	if _refresh_accumulator >= 0.5:
		_refresh_accumulator = 0.0
		_refresh_dock_status()


func _on_start_requested() -> void:
	_server.start_server()
	_refresh_dock_status()


func _on_stop_requested() -> void:
	_server.stop_server()
	_refresh_dock_status()


func _on_restart_requested() -> void:
	_server.restart_server()
	_refresh_dock_status()


func _on_settings_applied(host: String, port: int, auto_start: bool, max_log_entries: int) -> void:
	_server.apply_settings(host, port, auto_start, max_log_entries)
	_sync_dock_settings()
	_refresh_dock_status()


func _refresh_dock_status() -> void:
	if _dock != null and _server != null:
		_dock.refresh(_server.get_status_snapshot())


func _sync_dock_settings() -> void:
	if _dock != null and _server != null:
		_dock.sync_settings(_server.get_status_snapshot())
