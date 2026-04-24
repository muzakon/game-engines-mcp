using System.Collections.Generic;
using Newtonsoft.Json;

namespace GameEngineMCP
{
    /// <summary>
    /// Represents a JSON response sent back to the MCP Python server.
    /// </summary>
    public class McpResponse
    {
        public int Id;
        public string Status; // "ok" or "error"
        public Dictionary<string, object> Data;
        public string Error;

        public McpResponse(int id, string status, Dictionary<string, object> data = null, string error = null)
        {
            Id = id;
            Status = status;
            Data = data ?? new Dictionary<string, object>();
            Error = error;
        }

        public static McpResponse Ok(int id, Dictionary<string, object> data = null)
        {
            return new McpResponse(id, "ok", data);
        }

        public static McpResponse Err(int id, string error, Dictionary<string, object> data = null)
        {
            return new McpResponse(id, "error", data, error);
        }

        public string ToJson()
        {
            var obj = new Dictionary<string, object>
            {
                ["id"] = Id,
                ["status"] = Status
            };

            if (Data != null && Data.Count > 0)
                obj["data"] = Data;

            if (!string.IsNullOrEmpty(Error))
                obj["error"] = Error;

            return JsonConvert.SerializeObject(obj, Formatting.None);
        }
    }
}
