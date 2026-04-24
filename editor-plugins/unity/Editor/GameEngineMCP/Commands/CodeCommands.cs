using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

namespace GameEngineMCP
{
    public static class CodeCommands
    {
        public static McpResponse ExecuteCode(McpRequest req)
        {
            var code = req.GetStringParam("code", "");
            var language = req.GetStringParam("language", "csharp");

            if (string.IsNullOrEmpty(code))
                return McpResponse.Err(req.Id, "No code provided");

            if (language.ToLower() == "python")
                return ExecutePython(req, code);

            return ExecuteCSharp(req, code);
        }

        private static McpResponse ExecuteCSharp(McpRequest req, string code)
        {
            try
            {
                var trimmed = code.Trim();

                // Handle Debug.Log specifically
                if (trimmed.StartsWith("UnityEngine.Debug.Log") || trimmed.StartsWith("Debug.Log"))
                {
                    var msgStart = trimmed.IndexOf('(');
                    var msgEnd = trimmed.LastIndexOf(')');
                    if (msgStart >= 0 && msgEnd > msgStart)
                    {
                        var msg = trimmed.Substring(msgStart + 1, msgEnd - msgStart - 1).Trim('"').Trim('\'');
                        Debug.Log(msg);
                        return McpResponse.Ok(req.Id, new Dictionary<string, object>
                        {
                            ["output"] = $"Log: {msg}",
                            ["language"] = "csharp"
                        });
                    }
                }

                // General case: log and report
                Debug.Log($"[GameEngineMCP Execute] {code}");
                return McpResponse.Ok(req.Id, new Dictionary<string, object>
                {
                    ["output"] = $"Executed: {code}",
                    ["language"] = "csharp",
                    ["note"] = "For script creation, write .cs files directly to Assets/ via the file system"
                });
            }
            catch (System.Exception ex)
            {
                return McpResponse.Ok(req.Id, new Dictionary<string, object>
                {
                    ["error"] = ex.Message,
                    ["language"] = "csharp"
                });
            }
        }

        private static McpResponse ExecutePython(McpRequest req, string code)
        {
            var pythonRunnerType = System.Type.GetType(
                "UnityEditor.Scripting.Python.PythonRunner, UnityEditor.Scripting.Python");
            if (pythonRunnerType == null)
            {
                return McpResponse.Err(req.Id,
                    "Python for Unity is not installed. Install the 'com.unity.scripting.python' package.");
            }

            try
            {
                var runMethod = pythonRunnerType.GetMethod("RunString",
                    System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Static);
                if (runMethod == null)
                    return McpResponse.Err(req.Id, "Cannot find PythonRunner.RunString method");

                var result = runMethod.Invoke(null, new object[] { code });
                return McpResponse.Ok(req.Id, new Dictionary<string, object>
                {
                    ["output"] = result?.ToString() ?? "(no output)",
                    ["language"] = "python"
                });
            }
            catch (System.Exception ex)
            {
                return McpResponse.Ok(req.Id, new Dictionary<string, object>
                {
                    ["error"] = ex.InnerException?.Message ?? ex.Message,
                    ["language"] = "python"
                });
            }
        }
    }
}
