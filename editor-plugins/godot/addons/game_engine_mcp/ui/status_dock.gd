@tool
extends PanelContainer

signal start_requested
signal stop_requested
signal restart_requested
signal settings_applied(host: String, port: int, auto_start: bool, max_log_entries: int)

var _host_input: LineEdit
var _port_input: SpinBox
var _auto_start_toggle: CheckBox
var _max_logs_input: SpinBox
var _status_label: Label
var _client_label: Label
var _error_label: Label
var _capture_label: Label


func _ready() -> void:
	name = "Game Engine MCP"

	var root: VBoxContainer = VBoxContainer.new()
	root.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	root.size_flags_vertical = Control.SIZE_EXPAND_FILL
	add_child(root)

	var title: Label = Label.new()
	title.text = "Game Engine MCP"
	root.add_child(title)

	var host_row: HBoxContainer = HBoxContainer.new()
	root.add_child(host_row)
	var host_label: Label = Label.new()
	host_label.text = "Host"
	host_row.add_child(host_label)
	_host_input = LineEdit.new()
	_host_input.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	host_row.add_child(_host_input)

	var port_row: HBoxContainer = HBoxContainer.new()
	root.add_child(port_row)
	var port_label: Label = Label.new()
	port_label.text = "Port"
	port_row.add_child(port_label)
	_port_input = SpinBox.new()
	_port_input.min_value = 1
	_port_input.max_value = 65535
	_port_input.step = 1
	_port_input.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	port_row.add_child(_port_input)

	_auto_start_toggle = CheckBox.new()
	_auto_start_toggle.text = "Auto start when plugin loads"
	root.add_child(_auto_start_toggle)

	var logs_row: HBoxContainer = HBoxContainer.new()
	root.add_child(logs_row)
	var logs_label: Label = Label.new()
	logs_label.text = "Max Logs"
	logs_row.add_child(logs_label)
	_max_logs_input = SpinBox.new()
	_max_logs_input.min_value = 50
	_max_logs_input.max_value = 5000
	_max_logs_input.step = 50
	_max_logs_input.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	logs_row.add_child(_max_logs_input)

	var buttons: HBoxContainer = HBoxContainer.new()
	root.add_child(buttons)

	var apply_button: Button = Button.new()
	apply_button.text = "Apply"
	apply_button.pressed.connect(_on_apply_pressed)
	buttons.add_child(apply_button)

	var start_button: Button = Button.new()
	start_button.text = "Start"
	start_button.pressed.connect(_on_start_pressed)
	buttons.add_child(start_button)

	var stop_button: Button = Button.new()
	stop_button.text = "Stop"
	stop_button.pressed.connect(_on_stop_pressed)
	buttons.add_child(stop_button)

	var restart_button: Button = Button.new()
	restart_button.text = "Restart"
	restart_button.pressed.connect(_on_restart_pressed)
	buttons.add_child(restart_button)

	_status_label = Label.new()
	root.add_child(_status_label)

	_client_label = Label.new()
	root.add_child(_client_label)

	_error_label = Label.new()
	root.add_child(_error_label)

	_capture_label = Label.new()
	_capture_label.text = "Console capture: limited to Game Engine MCP internal logs."
	root.add_child(_capture_label)


func refresh(status: Dictionary) -> void:
	if _host_input == null:
		return

	var running: bool = bool(status.get("running", false))
	_status_label.text = "Status: %s" % ("Running" if running else "Stopped")
	_client_label.text = "Clients: %d" % int(status.get("clientCount", 0))

	var last_error: String = str(status.get("lastError", ""))
	_error_label.text = "Last Error: %s" % (last_error if last_error != "" else "None")


func sync_settings(status: Dictionary) -> void:
	if _host_input == null:
		return

	_host_input.text = str(status.get("host", "127.0.0.1"))
	_port_input.value = int(status.get("port", 9879))
	_auto_start_toggle.button_pressed = bool(status.get("autoStart", true))
	_max_logs_input.value = int(status.get("maxLogEntries", 500))


func _on_apply_pressed() -> void:
	settings_applied.emit(
		_host_input.text,
		int(_port_input.value),
		_auto_start_toggle.button_pressed,
		int(_max_logs_input.value)
	)


func _on_start_pressed() -> void:
	start_requested.emit()


func _on_stop_pressed() -> void:
	stop_requested.emit()


func _on_restart_pressed() -> void:
	restart_requested.emit()
