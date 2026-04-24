using System.Collections.Generic;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace GameEngineMCP
{
    public static class SceneCommands
    {
        public static McpResponse NewScene(McpRequest req)
        {
            var setup = req.GetStringParam("setup", "default").ToLowerInvariant();
            var mode = req.GetStringParam("mode", "single").ToLowerInvariant();
            var newSceneSetup = setup == "empty" ? NewSceneSetup.EmptyScene : NewSceneSetup.DefaultGameObjects;
            var newSceneMode = mode == "additive" ? NewSceneMode.Additive : NewSceneMode.Single;
            var scene = EditorSceneManager.NewScene(newSceneSetup, newSceneMode);
            return McpResponse.Ok(req.Id, SerializeScene(scene));
        }

        public static McpResponse OpenScene(McpRequest req)
        {
            var path = req.GetStringParam("path", "");
            if (string.IsNullOrWhiteSpace(path))
                return McpResponse.Err(req.Id, "No scene path provided");

            path = UnityMcpUtility.NormalizeAssetPath(path);
            var mode = req.GetStringParam("mode", "single").ToLowerInvariant() == "additive"
                ? OpenSceneMode.Additive
                : OpenSceneMode.Single;
            var scene = EditorSceneManager.OpenScene(path, mode);
            return McpResponse.Ok(req.Id, SerializeScene(scene));
        }

        public static McpResponse CloseScene(McpRequest req)
        {
            var path = req.GetStringParam("path", "");
            var removeScene = req.GetBoolParam("removeScene", true);
            var scene = ResolveScene(path);
            if (!scene.IsValid())
                return McpResponse.Err(req.Id, $"Scene not found: '{path}'");
            var closed = EditorSceneManager.CloseScene(scene, removeScene);
            return McpResponse.Ok(req.Id, new Dictionary<string, object> { ["closed"] = closed, ["path"] = path });
        }

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
            return McpResponse.Ok(req.Id, SerializeScene(scene));
        }

        public static McpResponse GetOpenScenes(McpRequest req)
        {
            var scenes = new List<Dictionary<string, object>>();
            for (var i = 0; i < SceneManager.sceneCount; i++)
            {
                scenes.Add(SerializeScene(SceneManager.GetSceneAt(i)));
            }
            return McpResponse.Ok(req.Id, new Dictionary<string, object>
            {
                ["scenes"] = scenes,
                ["count"] = scenes.Count
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

        public static McpResponse SaveAllScenes(McpRequest req)
        {
            var saved = EditorSceneManager.SaveOpenScenes();
            return McpResponse.Ok(req.Id, new Dictionary<string, object> { ["saved"] = saved });
        }

        public static McpResponse MarkSceneDirty(McpRequest req)
        {
            var path = req.GetStringParam("path", "");
            var scene = ResolveScene(path);
            if (!scene.IsValid())
                return McpResponse.Err(req.Id, $"Scene not found: '{path}'");
            var marked = EditorSceneManager.MarkSceneDirty(scene);
            return McpResponse.Ok(req.Id, new Dictionary<string, object>
            {
                ["markedDirty"] = marked,
                ["scene"] = SerializeScene(scene)
            });
        }

        internal static Dictionary<string, object> SerializeGameObject(GameObject obj)
        {
            var result = new Dictionary<string, object>
            {
                ["name"] = obj.name,
                ["active"] = obj.activeSelf,
                ["layer"] = LayerMask.LayerToName(obj.layer),
                ["tag"] = obj.tag,
                ["entityId"] = UnityMcpUtility.GetObjectId(obj),
                ["instanceId"] = obj.GetInstanceID(),
                ["path"] = UnityMcpUtility.GetHierarchyPath(obj)
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

        private static Scene ResolveScene(string pathOrName)
        {
            if (string.IsNullOrWhiteSpace(pathOrName))
                return SceneManager.GetActiveScene();

            for (var i = 0; i < SceneManager.sceneCount; i++)
            {
                var scene = SceneManager.GetSceneAt(i);
                if (scene.path == pathOrName || scene.name == pathOrName)
                    return scene;
            }
            return default(Scene);
        }

        private static Dictionary<string, object> SerializeScene(Scene scene)
        {
            return new Dictionary<string, object>
            {
                ["name"] = scene.name,
                ["path"] = scene.path,
                ["isDirty"] = scene.isDirty,
                ["isLoaded"] = scene.isLoaded,
                ["isValid"] = scene.IsValid(),
                ["rootCount"] = scene.rootCount,
                ["buildIndex"] = scene.buildIndex
            };
        }
    }
}
