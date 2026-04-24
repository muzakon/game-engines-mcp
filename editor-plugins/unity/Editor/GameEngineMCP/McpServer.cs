using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
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
    ///     via Unity's SynchronizationContext.
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
        private static readonly ManualResetEventSlim _stopSignal = new ManualResetEventSlim(false);
        private static readonly SynchronizationContext _unityContext;
        private static int _drainScheduled;

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
            _unityContext = SynchronizationContext.Current;
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
                    _stopSignal.Reset();
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
            _stopSignal.Set();
            lock (_streamLock)
            {
                _stream?.Close();
                _stream = null;
                _client?.Close();
                _client = null;
                _listener?.Stop();
                _listener = null;
            }

            // Drain any pending commands so their reader waits are released.
            while (_commandQueue.TryDequeue(out var pending))
            {
                pending.Completion.TrySetResult(new McpResponse(pending.RequestId, "error", error: "Server shutting down"));
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
                        _client.NoDelay = true;
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
                        _stopSignal.Wait(1000);
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
                    NetworkStream stream;
                    lock (_streamLock)
                    {
                        if (_stream == null) break;
                        stream = _stream;
                    }

                    bytesRead = stream.Read(buffer, 0, buffer.Length);

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
                catch (ObjectDisposedException) when (!_running)
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
                Completion = new TaskCompletionSource<McpResponse>()
            };

            _commandQueue.Enqueue(pending);
            ScheduleQueueDrain();

            // Block the reader thread until the main thread has processed this command.
            // This preserves request-response ordering.
            if (!pending.Completion.Task.Wait(30000))
            {
                Interlocked.Exchange(ref pending.Cancelled, 1);
                SendResponse(new McpResponse(requestId, "error", error: "Command timed out waiting for Unity main thread"));
                return;
            }

            SendResponse(pending.Completion.Task.Result);
        }

        /// <summary>
        /// Schedules a single main-thread callback that drains the entire queue.
        /// Re-entrant calls are safe: if a drain is already scheduled,
        /// callers reuse that pending drain.
        /// </summary>
        private static void ScheduleQueueDrain()
        {
            if (Interlocked.Exchange(ref _drainScheduled, 1) == 1)
                return;

            if (_unityContext != null)
            {
                _unityContext.Post(_ => DrainCommandQueue(), null);
                return;
            }

            EditorApplication.delayCall += DrainCommandQueue;
        }

        private static void DrainCommandQueue()
        {
            Interlocked.Exchange(ref _drainScheduled, 0);

            try
            {
                while (_commandQueue.TryDequeue(out var pending))
                {
                    if (Interlocked.CompareExchange(ref pending.Cancelled, 0, 0) == 1)
                        continue;

                    try
                    {
                        var request = McpRequest.FromJson(pending.Json);
                        pending.Completion.TrySetResult(CommandRouter.Route(request));
                    }
                    catch (Exception ex)
                    {
                        pending.Completion.TrySetResult(McpResponse.Err(
                            pending.RequestId,
                            $"Parse error: {ex.Message}",
                            UnityMcpUtility.SerializeException(ex)
                        ));
                    }
                }
            }
            finally
            {
                if (!_commandQueue.IsEmpty)
                    ScheduleQueueDrain();
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
            public int Cancelled;
            public TaskCompletionSource<McpResponse> Completion;
        }
    }
}
