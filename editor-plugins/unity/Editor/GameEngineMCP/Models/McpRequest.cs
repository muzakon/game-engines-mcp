using System.Collections.Generic;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

namespace GameEngineMCP
{
    /// <summary>
    /// Represents a JSON command received from the MCP Python server.
    /// </summary>
    public class McpRequest
    {
        public int Id;
        public string Command;
        public Dictionary<string, object> Params;

        public static McpRequest FromJson(string json)
        {
            var parsed = JsonConvert.DeserializeObject<Dictionary<string, object>>(json);
            if (parsed == null)
                throw new System.FormatException("Invalid JSON");

            var req = new McpRequest
            {
                Id = parsed.TryGetValue("id", out var idVal) ? System.Convert.ToInt32(idVal) : 0,
                Command = parsed.TryGetValue("command", out var cmdVal) ? cmdVal.ToString() : "",
                Params = new Dictionary<string, object>()
            };

            if (parsed.TryGetValue("params", out var paramsVal) && paramsVal is JObject obj)
            {
                req.Params = obj.ToObject<Dictionary<string, object>>() ?? new Dictionary<string, object>();
            }

            return req;
        }

        public string GetStringParam(string key, string defaultValue = "")
        {
            if (Params != null && Params.TryGetValue(key, out var val) && val != null)
                return val.ToString();
            return defaultValue;
        }

        public int GetIntParam(string key, int defaultValue = 0)
        {
            if (Params != null && Params.TryGetValue(key, out var val) && val != null)
            {
                try
                {
                    return System.Convert.ToInt32(val);
                }
                catch
                {
                    return defaultValue;
                }
            }
            return defaultValue;
        }

        public float GetFloatParam(string key, float defaultValue = 0f)
        {
            if (Params != null && Params.TryGetValue(key, out var val) && val != null)
                return System.Convert.ToSingle(val);
            return defaultValue;
        }

        public bool GetBoolParam(string key, bool defaultValue = false)
        {
            if (Params != null && Params.TryGetValue(key, out var val) && val != null)
                return System.Convert.ToBoolean(val);
            return defaultValue;
        }

        public List<object> GetListParam(string key)
        {
            if (Params != null && Params.TryGetValue(key, out var val))
                return UnityMcpUtility.ToList(val);
            return new List<object>();
        }

        public Dictionary<string, object> GetDictParam(string key)
        {
            if (Params != null && Params.TryGetValue(key, out var val))
                return UnityMcpUtility.ToDictionary(val);
            return new Dictionary<string, object>();
        }
    }
}
