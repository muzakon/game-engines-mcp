using System.Collections.Generic;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace GameEngineMCP
{
    public static class SceneCommands
    {
        public static McpResponse GetSceneHierarchy(McpRequest req)
        {
            var scene = SceneManager.GetActiveScene();
            if (!scene.isLoaded)
            {
                return McpResponse.Err(req.Id, "No active scene loaded");
            }

            var rootObjects = scene.GetRootGameObjects();
            var children = new List<Dictionary<string, object>>();
            foreach (var obj in rootObjects)
            {
                children.Add(SerializeGameObject(obj));
            }

            return McpResponse.Ok(req.Id, new Dictionary<string, object>
            {
                ["name"] = scene.name,
                ["path"] = scene.path,
                ["isDirty"] = scene.isDirty,
                ["rootCount"] = scene.rootCount,
                ["children"] = children
            });
        }

        public static McpResponse GetActiveScene(McpRequest req)
        {
            var scene = SceneManager.GetActiveScene();
            return McpResponse.Ok(req.Id, new Dictionary<string, object>
            {
                ["name"] = scene.name,
                ["path"] = scene.path,
                ["isDirty"] = scene.isDirty,
                ["isLoaded"] = scene.isLoaded,
                ["rootCount"] = scene.rootCount
            });
        }

        public static McpResponse SaveScene(McpRequest req)
        {
            var path = req.GetStringParam("path", "");
            var scene = SceneManager.GetActiveScene();

            if (!string.IsNullOrEmpty(path))
            {
                EditorSceneManager.SaveScene(scene, path);
                return McpResponse.Ok(req.Id, new Dictionary<string, object> { ["savedTo"] = path });
            }

            if (string.IsNullOrEmpty(scene.path))
            {
                return McpResponse.Err(req.Id, "Scene has no path. Save it manually first or provide a path parameter.");
            }

            EditorSceneManager.SaveScene(scene);
            return McpResponse.Ok(req.Id, new Dictionary<string, object> { ["savedTo"] = scene.path });
        }

        internal static Dictionary<string, object> SerializeGameObject(GameObject obj)
        {
            var result = new Dictionary<string, object>
            {
                ["name"] = obj.name,
                ["active"] = obj.activeSelf,
                ["layer"] = LayerMask.LayerToName(obj.layer),
                ["tag"] = obj.tag,
                ["instanceId"] = obj.GetInstanceID()
            };

            // Transform
            var t = obj.transform;
            result["position"] = new List<object> { t.position.x, t.position.y, t.position.z };
            result["rotation"] = new List<object> { t.rotation.eulerAngles.x, t.rotation.eulerAngles.y, t.rotation.eulerAngles.z };
            result["scale"] = new List<object> { t.localScale.x, t.localScale.y, t.localScale.z };

            // Components
            var components = new List<Dictionary<string, object>>();
            foreach (var comp in obj.GetComponents<Component>())
            {
                if (comp == null) continue;
                components.Add(new Dictionary<string, object>
                {
                    ["type"] = comp.GetType().Name,
                    ["enabled"] = (comp is MonoBehaviour mb) ? mb.enabled : true
                });
            }
            result["components"] = components;

            // Children
            var children = new List<Dictionary<string, object>>();
            foreach (Transform child in t)
            {
                children.Add(SerializeGameObject(child.gameObject));
            }
            result["children"] = children;

            return result;
        }
    }
}
