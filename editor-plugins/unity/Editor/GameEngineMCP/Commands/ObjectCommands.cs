using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

namespace GameEngineMCP
{
    public static class ObjectCommands
    {
        public static McpResponse GetObject(McpRequest req)
        {
            var path = req.GetStringParam("path", "");
            var instanceId = req.GetIntParam("instanceId", -1);

            GameObject obj = null;

            if (instanceId > 0)
            {
                obj = EditorUtility.InstanceIDToObject(instanceId) as GameObject;
            }

            if (obj == null && !string.IsNullOrEmpty(path))
            {
                obj = GameObject.Find(path);
            }

            if (obj == null)
            {
                // Try finding by name only (last segment of path)
                var name = path;
                if (path.Contains("/"))
                    name = path.Substring(path.LastIndexOf('/') + 1);

                var all = GameObject.FindObjectsOfType<GameObject>();
                foreach (var go in all)
                {
                    if (go.name == name)
                    {
                        obj = go;
                        break;
                    }
                }
            }

            if (obj == null)
            {
                return McpResponse.Err(req.Id, $"Object not found: '{path}'");
            }

            return McpResponse.Ok(req.Id, SceneCommands.SerializeGameObject(obj));
        }

        public static McpResponse CreateObject(McpRequest req)
        {
            var name = req.GetStringParam("name", "NewObject");
            var type = req.GetStringParam("type", "Empty");
            var parentPath = req.GetStringParam("parent", "");

            GameObject newObj;

            switch (type.ToLower())
            {
                case "cube":
                    newObj = GameObject.CreatePrimitive(PrimitiveType.Cube);
                    break;
                case "sphere":
                    newObj = GameObject.CreatePrimitive(PrimitiveType.Sphere);
                    break;
                case "cylinder":
                    newObj = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
                    break;
                case "capsule":
                    newObj = GameObject.CreatePrimitive(PrimitiveType.Capsule);
                    break;
                case "plane":
                    newObj = GameObject.CreatePrimitive(PrimitiveType.Plane);
                    break;
                case "quad":
                    newObj = GameObject.CreatePrimitive(PrimitiveType.Quad);
                    break;
                case "empty":
                default:
                    newObj = new GameObject();
                    break;
            }

            newObj.name = name;

            // Parent if specified
            if (!string.IsNullOrEmpty(parentPath))
            {
                var parent = GameObject.Find(parentPath);
                if (parent != null)
                {
                    newObj.transform.SetParent(parent.transform);
                }
            }

            // Register undo
            Undo.RegisterCreatedObjectUndo(newObj, $"MCP Create {name}");

            Selection.activeGameObject = newObj;

            return McpResponse.Ok(req.Id, new Dictionary<string, object>
            {
                ["name"] = newObj.name,
                ["instanceId"] = newObj.GetInstanceID(),
                ["type"] = type
            });
        }

        public static McpResponse DeleteObject(McpRequest req)
        {
            var path = req.GetStringParam("path", "");
            var obj = GameObject.Find(path);

            if (obj == null)
            {
                return McpResponse.Err(req.Id, $"Object not found: '{path}'");
            }

            var name = obj.name;
            Undo.DestroyObjectImmediate(obj);

            return McpResponse.Ok(req.Id, new Dictionary<string, object> { ["deleted"] = name });
        }

        public static McpResponse MoveObject(McpRequest req)
        {
            var path = req.GetStringParam("path", "");
            var obj = GameObject.Find(path);

            if (obj == null)
            {
                return McpResponse.Err(req.Id, $"Object not found: '{path}'");
            }

            var parentPath = req.GetStringParam("parent", "");
            if (!string.IsNullOrEmpty(parentPath))
            {
                var parent = GameObject.Find(parentPath);
                if (parent != null)
                    obj.transform.SetParent(parent.transform);
                else
                    return McpResponse.Err(req.Id, $"Parent not found: '{parentPath}'");
            }

            var t = obj.transform;
            var position = req.GetListParam("position");
            if (position.Count >= 3)
            {
                t.position = new Vector3(
                    (float)(double)position[0],
                    (float)(double)position[1],
                    (float)(double)position[2]
                );
            }

            var rotation = req.GetListParam("rotation");
            if (rotation.Count >= 3)
            {
                t.rotation = Quaternion.Euler(
                    (float)(double)rotation[0],
                    (float)(double)rotation[1],
                    (float)(double)rotation[2]
                );
            }

            var scale = req.GetListParam("scale");
            if (scale.Count >= 3)
            {
                t.localScale = new Vector3(
                    (float)(double)scale[0],
                    (float)(double)scale[1],
                    (float)(double)scale[2]
                );
            }

            return McpResponse.Ok(req.Id, new Dictionary<string, object>
            {
                ["name"] = obj.name,
                ["position"] = new List<object> { t.position.x, t.position.y, t.position.z },
                ["rotation"] = new List<object> { t.rotation.eulerAngles.x, t.rotation.eulerAngles.y, t.rotation.eulerAngles.z },
                ["scale"] = new List<object> { t.localScale.x, t.localScale.y, t.localScale.z }
            });
        }
    }
}
