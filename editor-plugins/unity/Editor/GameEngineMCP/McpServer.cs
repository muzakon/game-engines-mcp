using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEngine;

namespace GameEngineMCP
{
    /// <summary>
    /// TCP server that runs inside the Unity Editor and accepts JSON commands
    /// from the game-engine-mcp Python server.
    ///
    /// Architecture:
    ///   - A background listener thread accepts one client at a time and reads
    ///     newline-delimited JSON messages via a blocking read loop (no polling).
    ///   - Incoming commands are queued and drained on the Unity main thread
    ///     via EditorApplication.delayCall, avoiding ManualResetEvent blocking.
    ///   - Responses are written back on the background thread after the main
    ///     thread signals completion.
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
        private static volatile bool _running;
        private static readonly object _streamLock = new object();

        // Command queue: background thread enqueues, main thread drains.
        private static readonly ConcurrentQueue<PendingCommand> _commandQueue = new ConcurrentQueue<PendingCommand>();

        private static int _port = 9877;
        private static string _host = "127.0.0.1";
        private static bool _autoStart = true;

        public static bool IsRunning => _running;
        public static bool ClientConnected => _client != null && _client.Connected;
        public static int Port => _port;
        public static string Host => _host;
        public static bool AutoStart => _autoStart;

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
            lock (_streamLock)
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
            lock (_streamLock)
            {
                _stream?.Close();
                _stream = null;
                _client?.Close();
                _client = null;
                _listener?.Stop();
                _listener = null;
            }

            // Drain any pending commands so their wait handles are signaled.
            while (_commandQueue.TryDequeue(out var pending))
            {
                pending.Response = new McpResponse(pending.RequestId, "error", error: "Server shutting down");
                pending.Completed.Set();
            }

            Debug.Log("[GameEngineMCP] Server stopped");
        }

        public static void Restart()
        {
            Stop();
            Start();
        }

        // ------------------------------------------------------------------
        // Background thread: accept clients, read messages, enqueue commands
        // ------------------------------------------------------------------

        private static void ListenForClients()
        {
            while (_running)
            {
                try
                {
                    // Blocking accept -- no polling. The listener is stopped
                    // on Stop(), which will wake this up via SocketException.
                    var client = _listener.AcceptTcpClient();
                    lock (_streamLock)
                    {
                        _client?.Close();
                        _client = client;
                        _stream = _client.GetStream();
                    }

                    Debug.Log("[GameEngineMCP] Client connected");

                    // Start the pump that schedules main-thread processing.
                    ScheduleQueueDrain();
                    ReadClientLoop();
                }
                catch (SocketException ex) when (!_running)
                {
                    Debug.Log($"[GameEngineMCP] Listener socket closed: {ex.Message}");
                    break;
                }
                catch (ThreadAbortException)
                {
                    break;
                }
                catch (Exception ex)
                {
                    if (_running)
                    {
                        Debug.LogError($"[GameEngineMCP] Listener error: {ex.Message}\n{ex.StackTrace}");
                        Thread.Sleep(1000);
                    }
                }
            }
        }

        private static void ReadClientLoop()
        {
            var buffer = new byte[65536];
            var pendingData = new StringBuilder();

            while (_running && _client != null && _client.Connected)
            {
                try
                {
                    int bytesRead;
                    lock (_streamLock)
                    {
                        if (_stream == null) break;
                        bytesRead = _stream.Read(buffer, 0, buffer.Length);
                    }

                    if (bytesRead == 0)
                    {
                        Debug.Log("[GameEngineMCP] Client disconnected");
                        break;
                    }

                    pendingData.Append(Encoding.UTF8.GetString(buffer, 0, bytesRead));

                    // Extract complete messages (newline-delimited JSON).
                    var data = pendingData.ToString();
                    int newlineIdx;
                    while ((newlineIdx = data.IndexOf('\n')) >= 0)
                    {
                        var line = data.Substring(0, newlineIdx).Trim();
                        data = data.Substring(newlineIdx + 1);

                        if (!string.IsNullOrEmpty(line))
                        {
                            EnqueueCommand(line);
                        }
                    }
                    pendingData.Clear();
                    pendingData.Append(data);
                }
                catch (IOException ex) when (!_running)
                {
                    break;
                }
                catch (Exception ex)
                {
                    Debug.LogError($"[GameEngineMCP] Client error: {ex.Message}\n{ex.StackTrace}");
                    break;
                }
            }

            lock (_streamLock)
            {
                _stream = null;
                _client = null;
            }
        }

        // ------------------------------------------------------------------
        // Command dispatch: background -> queue -> main thread
        // ------------------------------------------------------------------

        private static void EnqueueCommand(string json)
        {
            int requestId = 0;
            try
            {
                var parsed = JObject.Parse(json);
                requestId = parsed.TryGetValue("id", out var idToken) ? idToken.Value<int>() : 0;
            }
            catch
            {
                // Will be caught again during main-thread processing.
            }

            var pending = new PendingCommand
            {
                Json = json,
                RequestId = requestId,
                Completed = new ManualResetEventSlim(false)
            };

            _commandQueue.Enqueue(pending);
            ScheduleQueueDrain();

            // Block the reader thread until the main thread has processed this command.
            // This preserves request-response ordering.
            if (!pending.Completed.Wait(30000))
            {
                SendResponse(new McpResponse(requestId, "error", error: "Command timed out waiting for Unity main thread"));
                return;
            }

            SendResponse(pending.Response);
            pending.Completed.Dispose();
        }

        /// <summary>
        /// Schedules a single delayCall that drains the entire queue.
        /// Re-entrant calls are safe: if the queue is already being drained,
        /// the extra delayCall simply finds nothing to do.
        /// </summary>
        private static void ScheduleQueueDrain()
        {
            EditorApplication.delayCall -= DrainCommandQueue;
            EditorApplication.delayCall += DrainCommandQueue;
        }

        private static void DrainCommandQueue()
        {
            while (_commandQueue.TryDequeue(out var pending))
            {
                try
                {
                    var request = McpRequest.FromJson(pending.Json);
                    pending.Response = CommandRouter.Route(request);
                }
                catch (Exception ex)
                {
                    pending.Response = new McpResponse(pending.RequestId, "error", error: $"Parse error: {ex.Message}");
                }
                finally
                {
                    pending.Completed.Set();
                }
            }
        }

        // ------------------------------------------------------------------
        // Response sending
        // ------------------------------------------------------------------

        private static void SendResponse(McpResponse response)
        {
            if (response == null) return;
            try
            {
                var json = response.ToJson() + "\n";
                var bytes = Encoding.UTF8.GetBytes(json);
                lock (_streamLock)
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

        // ------------------------------------------------------------------
        // Settings persistence
        // ------------------------------------------------------------------

        private static void LoadSettings()
        {
            try
            {
                var settingsPath = Path.Combine(
                    Application.dataPath, "..",
                    "ProjectSettings", "GameEngineMCP.json"
                );
                if (File.Exists(settingsPath))
                {
                    var json = File.ReadAllText(settingsPath);
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
                var settingsPath = Path.Combine(
                    Application.dataPath, "..",
                    "ProjectSettings", "GameEngineMCP.json"
                );
                var settings = new Dictionary<string, object>
                {
                    ["port"] = _port,
                    ["host"] = _host,
                    ["autoStart"] = _autoStart
                };
                var json = JsonConvert.SerializeObject(settings, Formatting.Indented);
                File.WriteAllText(settingsPath, json);
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

        // ------------------------------------------------------------------
        // Internal types
        // ------------------------------------------------------------------

        private class PendingCommand
        {
            public string Json;
            public int RequestId;
            public McpResponse Response;
            public ManualResetEventSlim Completed;
        }
    }
}
