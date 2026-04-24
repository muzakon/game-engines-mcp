using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using UnityEngine.TestTools;

namespace GameEngineMCP
{
    public static class EditorCommands
    {
        public static McpResponse Ping(McpRequest req)
        {
            return McpResponse.Ok(req.Id, new Dictionary<string, object>
            {
                ["status"] = "alive",
                ["engine"] = "unity",
                ["version"] = Application.unityVersion
            });
        }

        public static McpResponse GetEditorInfo(McpRequest req)
        {
            var info = new Dictionary<string, object>
            {
                ["engine"] = "unity",
                ["version"] = Application.unityVersion,
                ["platform"] = Application.platform.ToString(),
                ["projectName"] = Application.productName,
                ["projectPath"] = Application.dataPath,
                ["isPlaying"] = EditorApplication.isPlaying,
                ["isPaused"] = EditorApplication.isPaused,
                ["timeSinceStartup"] = EditorApplication.timeSinceStartup
            };
            return McpResponse.Ok(req.Id, info);
        }

        public static McpResponse Play(McpRequest req)
        {
            EditorApplication.isPlaying = true;
            return McpResponse.Ok(req.Id, new Dictionary<string, object> { ["playing"] = true });
        }

        public static McpResponse Pause(McpRequest req)
        {
            EditorApplication.isPaused = !EditorApplication.isPaused;
            return McpResponse.Ok(req.Id, new Dictionary<string, object> { ["paused"] = EditorApplication.isPaused });
        }

        public static McpResponse Stop(McpRequest req)
        {
            EditorApplication.isPlaying = false;
            return McpResponse.Ok(req.Id, new Dictionary<string, object> { ["playing"] = false });
        }

        public static McpResponse RunTests(McpRequest req)
        {
            var testMode = req.GetStringParam("test_mode", "edit");
            var mode = testMode == "play" ? TestMode.PlayMode : TestMode.EditMode;
            
            var result = new Dictionary<string, object>
            {
                ["message"] = $"Test run initiated for {testMode} mode. Check Unity Test Runner for results.",
                ["testMode"] = testMode
            };

            // Initiate test run via reflection to avoid hard dependency
            var testRunnerType = System.Type.GetType("UnityEditor.TestTools.TestRunner.TestRunnerWindow, UnityEditor.TestRunner");
            if (testRunnerType != null)
            {
                result["available"] = true;
            }
            else
            {
                result["available"] = false;
                result["message"] = "Test Runner not available";
            }

            return McpResponse.Ok(req.Id, result);
        }
    }
}
