using UnityEditor;
using UnityEngine;

namespace GameEngineMCP
{
    public class McpSettingsWindow : EditorWindow
    {
        private string _host = "127.0.0.1";
        private int _port = 9877;
        private bool _autoStart = true;

        [MenuItem("Tools/Game Engine MCP/Settings")]
        public static void ShowWindow()
        {
            var window = GetWindow<McpSettingsWindow>("Game Engine MCP");
            window.minSize = new Vector2(300, 180);
        }

        [MenuItem("Tools/Game Engine MCP/Start Server")]
        public static void StartServer()
        {
            McpServer.Start();
        }

        [MenuItem("Tools/Game Engine MCP/Stop Server")]
        public static void StopServer()
        {
            McpServer.Stop();
        }

        [MenuItem("Tools/Game Engine MCP/Restart Server")]
        public static void RestartServer()
        {
            McpServer.Restart();
        }

        private void OnEnable()
        {
            _host = McpServer.Host;
            _port = McpServer.Port;
            _autoStart = true; // TODO: load from settings
        }

        private void OnGUI()
        {
            EditorGUILayout.LabelField("Game Engine MCP", EditorStyles.boldLabel);
            EditorGUILayout.Space(8);

            EditorGUI.BeginChangeCheck();
            _host = EditorGUILayout.TextField("Host", _host);
            _port = EditorGUILayout.IntField("Port", _port);
            _autoStart = EditorGUILayout.Toggle("Auto Start", _autoStart);
            if (EditorGUI.EndChangeCheck())
            {
                McpServer.Configure(_host, _port, _autoStart);
            }

            EditorGUILayout.Space(8);

            // Status
            var status = McpServer.IsRunning
                ? $"<color=green>Running</color> on {_host}:{_port}"
                : "<color=red>Stopped</color>";
            EditorGUILayout.LabelField("Status", status, new GUIStyle(EditorStyles.label) { richText = true });
            EditorGUILayout.LabelField("Client", McpServer.ClientConnected ? "Connected" : "Waiting...");

            EditorGUILayout.Space(8);

            // Buttons
            EditorGUILayout.BeginHorizontal();
            if (!McpServer.IsRunning)
            {
                if (GUILayout.Button("Start", GUILayout.Height(30)))
                    McpServer.Start();
            }
            else
            {
                if (GUILayout.Button("Stop", GUILayout.Height(30)))
                    McpServer.Stop();
            }

            if (McpServer.IsRunning)
            {
                if (GUILayout.Button("Restart", GUILayout.Height(30)))
                    McpServer.Restart();
            }
            EditorGUILayout.EndHorizontal();

            EditorGUILayout.Space(8);
            EditorGUILayout.HelpBox(
                "Copy this folder into your Unity project's Assets/Editor/ directory, " +
                "or install as a local package via Package Manager > Add package from disk.",
                MessageType.Info
            );
        }
    }
}
