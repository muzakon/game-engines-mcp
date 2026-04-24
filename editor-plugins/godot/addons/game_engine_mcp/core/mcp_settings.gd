@tool
extends RefCounted
class_name McpSettings

const SETTINGS_PATH := "user://game_engine_mcp.cfg"
const CONFIG_SECTION := "server"

var host: String = "127.0.0.1"
var port: int = 9879
var auto_start: bool = true
var max_log_entries: int = 500


static func load_or_default() -> RefCounted:
	var settings: McpSettings = McpSettings.new()
	var config: ConfigFile = ConfigFile.new()
	var err: int = config.load(SETTINGS_PATH)
	if err != OK:
		return settings

	settings.host = str(config.get_value(CONFIG_SECTION, "host", settings.host))
	settings.port = int(config.get_value(CONFIG_SECTION, "port", settings.port))
	settings.auto_start = bool(config.get_value(CONFIG_SECTION, "auto_start", settings.auto_start))
	settings.max_log_entries = int(config.get_value(CONFIG_SECTION, "max_log_entries", settings.max_log_entries))
	settings.normalize()
	return settings


func save() -> int:
	normalize()
	var config: ConfigFile = ConfigFile.new()
	config.set_value(CONFIG_SECTION, "host", host)
	config.set_value(CONFIG_SECTION, "port", port)
	config.set_value(CONFIG_SECTION, "auto_start", auto_start)
	config.set_value(CONFIG_SECTION, "max_log_entries", max_log_entries)
	return config.save(SETTINGS_PATH)


func normalize() -> void:
	host = host.strip_edges()
	if host == "":
		host = "127.0.0.1"
	port = clampi(port, 1, 65535)
	max_log_entries = clampi(max_log_entries, 50, 5000)


func to_dictionary() -> Dictionary:
	return {
		"host": host,
		"port": port,
		"autoStart": auto_start,
		"maxLogEntries": max_log_entries,
	}
