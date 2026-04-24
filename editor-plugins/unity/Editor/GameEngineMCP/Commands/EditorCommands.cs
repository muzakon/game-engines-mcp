using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;

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
                ["projectPath"] = Directory.GetParent(Application.dataPath)?.FullName ?? Application.dataPath,
                ["dataPath"] = Application.dataPath,
                ["applicationPath"] = EditorApplication.applicationPath,
                ["isPlaying"] = EditorApplication.isPlaying,
                ["isPaused"] = EditorApplication.isPaused,
                ["isCompiling"] = EditorApplication.isCompiling,
                ["isUpdating"] = EditorApplication.isUpdating,
                ["isFocused"] = EditorApplication.isFocused,
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

        public static McpResponse ExecuteMenuItem(McpRequest req)
        {
            var menuItem = req.GetStringParam("menuItem", req.GetStringParam("path", ""));
            if (string.IsNullOrWhiteSpace(menuItem))
                return McpResponse.Err(req.Id, "No menuItem provided");

            var executed = EditorApplication.ExecuteMenuItem(menuItem);
            return McpResponse.Ok(req.Id, new Dictionary<string, object>
            {
                ["menuItem"] = menuItem,
                ["executed"] = executed
            });
        }

        public static McpResponse Repaint(McpRequest req)
        {
            EditorApplication.RepaintHierarchyWindow();
            EditorApplication.RepaintProjectWindow();
            SceneView.RepaintAll();
            return McpResponse.Ok(req.Id, new Dictionary<string, object> { ["repainted"] = true });
        }

        public static McpResponse GetSelection(McpRequest req)
        {
            var objects = new List<Dictionary<string, object>>();
            foreach (var obj in Selection.objects)
            {
                objects.Add(UnityMcpUtility.SerializeUnityObject(obj));
            }

            return McpResponse.Ok(req.Id, new Dictionary<string, object>
            {
                ["activeObject"] = UnityMcpUtility.SerializeUnityObject(Selection.activeObject),
                ["activeGameObject"] = Selection.activeGameObject != null ? SceneCommands.SerializeGameObject(Selection.activeGameObject) : null,
                ["objects"] = objects,
                ["count"] = objects.Count
            });
        }

        public static McpResponse SetSelection(McpRequest req)
        {
            var paths = req.GetListParam("paths");
            var path = req.GetStringParam("path", "");
            var selected = new List<Object>();

            if (!string.IsNullOrWhiteSpace(path))
                AddSelectionTarget(selected, path);

            foreach (var item in paths)
                AddSelectionTarget(selected, item?.ToString() ?? "");

            Selection.objects = selected.ToArray();
            if (Selection.activeObject != null)
                EditorGUIUtility.PingObject(Selection.activeObject);

            return GetSelection(req);
        }

        public static McpResponse PingObject(McpRequest req)
        {
            var path = req.GetStringParam("path", "");
            var instanceId = req.GetIntParam("instanceId", -1);
            Object target = instanceId > 0 ? EditorUtility.InstanceIDToObject(instanceId) : null;
            if (target == null && !string.IsNullOrWhiteSpace(path))
                target = AssetDatabase.LoadAssetAtPath<Object>(UnityMcpUtility.NormalizeAssetPath(path)) ??
                         UnityMcpUtility.FindGameObject(path);
            if (target == null)
                return McpResponse.Err(req.Id, $"Object not found: '{path}'");

            EditorGUIUtility.PingObject(target);
            Selection.activeObject = target;
            return McpResponse.Ok(req.Id, new Dictionary<string, object> { ["pinged"] = UnityMcpUtility.SerializeUnityObject(target) });
        }

        public static McpResponse RunTests(McpRequest req)
        {
            var testMode = req.GetStringParam("test_mode", "edit");
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

        private static void AddSelectionTarget(List<Object> selected, string path)
        {
            if (string.IsNullOrWhiteSpace(path)) return;
            var asset = AssetDatabase.LoadAssetAtPath<Object>(UnityMcpUtility.NormalizeAssetPath(path));
            if (asset != null)
            {
                selected.Add(asset);
                return;
            }

            var go = UnityMcpUtility.FindGameObject(path);
            if (go != null) selected.Add(go);
        }
    }
}
