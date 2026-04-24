using System;
using System.Collections.Generic;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEngine;

namespace GameEngineMCP
{
    /// <summary>
    /// TCP server that runs inside the Unity Editor and accepts JSON commands
    /// from the game-engine-mcp Python server.
    /// 
    /// Install: Copy this folder into your Unity project under Assets/Editor/ or
    /// as a local package via Package Manager.
    /// 
    /// Configure: Tools > Game Engine MCP > Settings (or edit ProjectSettings/GameEngineMCP.json)
    /// </summary>
    [InitializeOnLoad]
    public static class McpServer
    {
        private static TcpListener _listener;
        private static TcpClient _client;
        private static NetworkStream _stream;
        private static Thread _listenerThread;
        private static Thread _clientThread;
        private static volatile bool _running;
        private static readonly object _lock = new object();

        private static int _port = 9877;
        private static string _host = "127.0.0.1";
        private static bool _autoStart = true;

        public static bool IsRunning => _running;
        public static bool ClientConnected => _client != null && _client.Connected;
        public static int Port => _port;
        public static string Host => _host;

        static McpServer()
        {
            LoadSettings();
            if (_autoStart)
            {
                Start();
            }
        }

        public static void Start()
        {
            if (_running) return;
            lock (_lock)
            {
                if (_running) return;

                try
                {
                    var address = IPAddress.Parse(_host);
                    _listener = new TcpListener(address, _port);
                    _listener.Start();
                    _running = true;

                    _listenerThread = new Thread(ListenForClients)
                    {
                        IsBackground = true,
                        Name = "GameEngineMCP-Listener"
                    };
                    _listenerThread.Start();

                    Debug.Log($"[GameEngineMCP] Server started on {_host}:{_port}");
                }
                catch (Exception ex)
                {
                    Debug.LogError($"[GameEngineMCP] Failed to start: {ex.Message}");
                }
            }
        }

        public static void Stop()
        {
            _running = false;
            lock (_lock)
            {
                _stream?.Close();
                _stream = null;
                _client?.Close();
                _client = null;
                _listener?.Stop();
                _listener = null;
            }
            Debug.Log("[GameEngineMCP] Server stopped");
        }

        public static void Restart()
        {
            Stop();
            Start();
        }

        private static void ListenForClients()
        {
            while (_running)
            {
                try
                {
                    if (!_listener.Pending())
                    {
                        Thread.Sleep(100);
                        continue;
                    }

                    var client = _listener.AcceptTcpClient();
                    lock (_lock)
                    {
                        _client?.Close();
                        _client = client;
                        _stream = _client.GetStream();
                    }

                    Debug.Log("[GameEngineMCP] Client connected");

                    _clientThread = new Thread(HandleClient)
                    {
                        IsBackground = true,
                        Name = "GameEngineMCP-Client"
                    };
                    _clientThread.Start();
                }
                catch (SocketException)
                {
                    // Listener stopped
                    break;
                }
                catch (Exception ex)
                {
                    Debug.LogError($"[GameEngineMCP] Listener error: {ex.Message}");
                    Thread.Sleep(1000);
                }
            }
        }

        private static void HandleClient()
        {
            var buffer = new byte[65536];
            var pendingData = new StringBuilder();

            while (_running && _client != null && _client.Connected)
            {
                try
                {
                    int bytesRead;
                    lock (_lock)
                    {
                        if (_stream == null || !_stream.DataAvailable) 
                        {
                            Thread.Sleep(10);
                            continue;
                        }
                        bytesRead = _stream.Read(buffer, 0, buffer.Length);
                    }

                    if (bytesRead == 0)
                    {
                        Debug.Log("[GameEngineMCP] Client disconnected");
                        break;
                    }

                    pendingData.Append(Encoding.UTF8.GetString(buffer, 0, bytesRead));

                    // Process complete messages (newline-delimited JSON)
                    var data = pendingData.ToString();
                    int newlineIdx;
                    while ((newlineIdx = data.IndexOf('\n')) >= 0)
                    {
                        var line = data.Substring(0, newlineIdx).Trim();
                        data = data.Substring(newlineIdx + 1);

                        if (!string.IsNullOrEmpty(line))
                        {
                            ProcessCommand(line);
                        }
                    }
                    pendingData.Clear();
                    pendingData.Append(data);
                }
                catch (Exception ex)
                {
                    Debug.LogError($"[GameEngineMCP] Client error: {ex.Message}");
                    break;
                }
            }

            lock (_lock)
            {
                _stream = null;
                _client = null;
            }
        }

        private static void ProcessCommand(string json)
        {
            try
            {
                var request = McpRequest.FromJson(json);
                var response = CommandRouter.Route(request);
                SendResponse(response);
            }
            catch (Exception ex)
            {
                SendResponse(new McpResponse(0, "error", error: $"Parse error: {ex.Message}"));
            }
        }

        private static void SendResponse(McpResponse response)
        {
            try
            {
                var json = response.ToJson() + "\n";
                var bytes = Encoding.UTF8.GetBytes(json);
                lock (_lock)
                {
                    _stream?.Write(bytes, 0, bytes.Length);
                    _stream?.Flush();
                }
            }
            catch (Exception ex)
            {
                Debug.LogError($"[GameEngineMCP] Send error: {ex.Message}");
            }
        }

        // Settings persistence

        private static void LoadSettings()
        {
            try
            {
                var settingsPath = System.IO.Path.Combine(
                    UnityEngine.Application.dataPath, "..",
                    "ProjectSettings", "GameEngineMCP.json"
                );
                if (System.IO.File.Exists(settingsPath))
                {
                    var json = System.IO.File.ReadAllText(settingsPath);
                    var settings = JsonConvert.DeserializeObject<Dictionary<string, object>>(json);
                    if (settings != null)
                    {
                        if (settings.TryGetValue("port", out var portVal))
                            _port = Convert.ToInt32(portVal);
                        if (settings.TryGetValue("host", out var hostVal))
                            _host = hostVal.ToString();
                        if (settings.TryGetValue("autoStart", out var autoVal))
                            _autoStart = Convert.ToBoolean(autoVal);
                    }
                }
            }
            catch (Exception ex)
            {
                Debug.LogWarning($"[GameEngineMCP] Failed to load settings: {ex.Message}");
            }
        }

        public static void SaveSettings()
        {
            try
            {
                var settingsPath = System.IO.Path.Combine(
                    UnityEngine.Application.dataPath, "..",
                    "ProjectSettings", "GameEngineMCP.json"
                );
                var settings = new System.Collections.Generic.Dictionary<string, object>
                {
                    ["port"] = _port,
                    ["host"] = _host,
                    ["autoStart"] = _autoStart
                };
                var json = JsonConvert.SerializeObject(settings, Formatting.Indented);
                System.IO.File.WriteAllText(settingsPath, json);
            }
            catch (Exception ex)
            {
                Debug.LogWarning($"[GameEngineMCP] Failed to save settings: {ex.Message}");
            }
        }

        public static void Configure(string host, int port, bool autoStart)
        {
            _host = host;
            _port = port;
            _autoStart = autoStart;
            SaveSettings();
        }
    }
}
