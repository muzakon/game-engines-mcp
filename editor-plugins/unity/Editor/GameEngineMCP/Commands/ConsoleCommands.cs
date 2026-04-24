using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

namespace GameEngineMCP
{
    /// <summary>
    /// Captures and retrieves Unity console log entries.
    /// 
    /// Console log capture works by intercepting Application.logMessageReceived
    /// and storing entries in a ring buffer. Clear console uses reflection to
    /// clear the Console window.
    /// </summary>
    [InitializeOnLoad]
    public static class ConsoleCommands
    {
        private const int MAX_LOG_ENTRIES = 1000;
        private static readonly List<Dictionary<string, object>> _logEntries = new List<Dictionary<string, object>>();
        private static int _totalLogged = 0;

        static ConsoleCommands()
        {
            Application.logMessageReceived += OnLogMessageReceived;
        }

        private static void OnLogMessageReceived(string condition, string stackTrace, LogType type)
        {
            _totalLogged++;
            var entry = new Dictionary<string, object>
            {
                ["message"] = condition,
                ["stackTrace"] = stackTrace,
                ["level"] = LogTypeToString(type),
                ["index"] = _totalLogged
            };

            _logEntries.Add(entry);

            // Ring buffer: trim oldest entries
            while (_logEntries.Count > MAX_LOG_ENTRIES)
            {
                _logEntries.RemoveAt(0);
            }
        }

        public static McpResponse GetConsoleLogs(McpRequest req)
        {
            var count = req.GetIntParam("count", 50);
            var level = req.GetStringParam("level", "");

            var filtered = new List<Dictionary<string, object>>();
            
            for (int i = _logEntries.Count - 1; i >= 0 && filtered.Count < count; i--)
            {
                var entry = _logEntries[i];
                if (!string.IsNullOrEmpty(level) && entry["level"].ToString() != level.ToLower())
                    continue;
                filtered.Add(entry);
            }

            // Return in chronological order
            filtered.Reverse();

            return McpResponse.Ok(req.Id, new Dictionary<string, object>
            {
                ["logs"] = filtered,
                ["totalAvailable"] = _totalLogged,
                ["returned"] = filtered.Count
            });
        }

        public static McpResponse ClearConsole(McpRequest req)
        {
            _logEntries.Clear();
            _totalLogged = 0;

            // Also clear the actual Unity console
            var assembly = System.Reflection.Assembly.GetAssembly(typeof(EditorWindow));
            var consoleWindowType = assembly.GetType("UnityEditor.ConsoleWindow");
            if (consoleWindowType != null)
            {
                var clearMethod = consoleWindowType.GetMethod("Clear",
                    System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.Public);
                clearMethod?.Invoke(null, null);
            }

            return McpResponse.Ok(req.Id, new Dictionary<string, object> { ["cleared"] = true });
        }

        private static string LogTypeToString(LogType type)
        {
            return type switch
            {
                LogType.Error => "error",
                LogType.Assert => "error",
                LogType.Warning => "warning",
                LogType.Log => "log",
                LogType.Exception => "error",
                _ => "log"
            };
        }
    }
}
