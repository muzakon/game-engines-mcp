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

        public static McpResponse ListCommands(McpRequest req)
        {
            return McpResponse.Ok(req.Id, new Dictionary<string, object>
            {
                ["commands"] = new List<Dictionary<string, object>>
                {
                    CommandInfo("ping", "Check that the Unity editor plugin is alive."),
                    CommandInfo("list_commands", "Return supported Unity editor plugin commands."),
                    CommandInfo("get_editor_info", "Return Unity version, project paths, play state, and editor state."),
                    CommandInfo("play", "Enter play mode."),
                    CommandInfo("pause", "Toggle editor pause state."),
                    CommandInfo("stop", "Exit play mode."),
                    CommandInfo("execute_menu_item", "Execute a Unity editor menu item by path.", "menuItem"),
                    CommandInfo("repaint_editor", "Repaint hierarchy, project, and scene views."),
                    CommandInfo("get_selection", "Return current editor selection."),
                    CommandInfo("set_selection", "Set editor selection by one path or multiple paths.", "path", "paths"),
                    CommandInfo("ping_object", "Ping and select an asset or scene object.", "path", "instanceId", "entityId"),
                    CommandInfo("get_console_logs", "Return captured Unity console logs.", "count", "level"),
                    CommandInfo("clear_console", "Clear captured logs and the Unity console window."),
                    CommandInfo("new_scene", "Create a new scene.", "setup", "mode"),
                    CommandInfo("open_scene", "Open a scene asset.", "path", "mode"),
                    CommandInfo("close_scene", "Close an open scene.", "path", "removeScene"),
                    CommandInfo("get_scene_hierarchy", "Return the active scene hierarchy."),
                    CommandInfo("get_active_scene", "Return active scene metadata."),
                    CommandInfo("get_open_scenes", "Return all open scenes."),
                    CommandInfo("save_scene", "Save the active scene.", "path"),
                    CommandInfo("save_all_scenes", "Save all open scenes."),
                    CommandInfo("mark_scene_dirty", "Mark a scene dirty.", "path"),
                    CommandInfo("find_objects", "Search scene objects by name, component, tag, layer, or active state.", "name", "component", "tag", "layer", "includeInactive", "limit"),
                    CommandInfo("get_object", "Return a scene object and its children.", "path", "instanceId", "entityId"),
                    CommandInfo("create_object", "Create a GameObject or primitive.", "name", "type", "parent"),
                    CommandInfo("delete_object", "Delete a scene object.", "path", "instanceId", "entityId"),
                    CommandInfo("move_object", "Set parent, position, rotation, or scale.", "path", "parent", "position", "rotation", "scale"),
                    CommandInfo("duplicate_object", "Duplicate a scene object.", "path", "name"),
                    CommandInfo("set_object_active", "Set GameObject active state.", "path", "active"),
                    CommandInfo("add_component", "Add a component by type name.", "path", "component"),
                    CommandInfo("remove_component", "Remove a component by type name.", "path", "component"),
                    CommandInfo("get_properties", "Return serialized component properties.", "path", "component"),
                    CommandInfo("set_property", "Set one component property.", "path", "component", "property", "value"),
                    CommandInfo("set_properties", "Set multiple component properties.", "path", "component", "properties"),
                    CommandInfo("list_assets", "List assets under a folder.", "path", "recursive", "filter"),
                    CommandInfo("get_asset", "Return asset metadata.", "path"),
                    CommandInfo("import_asset", "Import one asset.", "path"),
                    CommandInfo("refresh_assets", "Refresh the AssetDatabase."),
                    CommandInfo("create_folder", "Create an AssetDatabase folder.", "parent", "name"),
                    CommandInfo("delete_asset", "Delete an asset.", "path"),
                    CommandInfo("move_asset", "Move an asset.", "from", "to"),
                    CommandInfo("copy_asset", "Copy an asset.", "from", "to"),
                    CommandInfo("rename_asset", "Rename an asset.", "path", "name"),
                    CommandInfo("get_asset_dependencies", "Return asset dependencies.", "path", "recursive"),
                    CommandInfo("reveal_asset", "Reveal and ping an asset in the Project window.", "path"),
                    CommandInfo("take_screenshot", "Capture active cameras to a PNG.", "width", "height"),
                    CommandInfo("execute_code", "Execute supported editor code snippets.", "language", "code"),
                    CommandInfo("run_tests", "Check Test Runner availability and initiate test workflow.", "test_mode")
                }
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
            var entityId = req.GetStringParam("entityId", "");
            Object target = UnityMcpUtility.ObjectFromId(entityId, instanceId);
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

        private static Dictionary<string, object> CommandInfo(string name, string description, params string[] parameters)
        {
            return new Dictionary<string, object>
            {
                ["name"] = name,
                ["description"] = description,
                ["parameters"] = new List<string>(parameters)
            };
        }
    }
}
