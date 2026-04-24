using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

namespace GameEngineMCP
{
    public static class ObjectCommands
    {
        /// <summary>
        /// Resolves a GameObject from standard request parameters.
        /// Looks up by entityId first, then instanceId, then path.
        /// </summary>
        private static GameObject ResolveObject(McpRequest req)
        {
            var path = req.GetStringParam("path", "");
            var instanceId = req.GetIntParam("instanceId", -1);
            var entityId = req.GetStringParam("entityId", "");
            return UnityMcpUtility.FindGameObject(path, instanceId, entityId);
        }

        public static McpResponse GetObject(McpRequest req)
        {
            var obj = ResolveObject(req);
            if (obj == null)
                return McpResponse.Err(req.Id, $"Object not found: '{req.GetStringParam("path", "")}'");
            return McpResponse.Ok(req.Id, SceneCommands.SerializeGameObject(obj));
        }

        public static McpResponse CreateObject(McpRequest req)
        {
            var name = req.GetStringParam("name", "NewObject");
            var type = req.GetStringParam("type", "Empty");
            var parentPath = req.GetStringParam("parent", "");

            GameObject newObj;

            switch (type.ToLowerInvariant())
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

            if (!string.IsNullOrEmpty(parentPath))
            {
                var parent = UnityMcpUtility.FindGameObject(parentPath);
                if (parent != null)
                    newObj.transform.SetParent(parent.transform);
            }

            Undo.RegisterCreatedObjectUndo(newObj, $"MCP Create {name}");
            Selection.activeGameObject = newObj;

            return McpResponse.Ok(req.Id, new Dictionary<string, object>
            {
                ["name"] = newObj.name,
                ["entityId"] = UnityMcpUtility.GetObjectId(newObj),
                ["instanceId"] = newObj.GetInstanceID(),
                ["type"] = type,
                ["path"] = UnityMcpUtility.GetHierarchyPath(newObj)
            });
        }

        public static McpResponse DeleteObject(McpRequest req)
        {
            var obj = ResolveObject(req);
            if (obj == null)
                return McpResponse.Err(req.Id, $"Object not found: '{req.GetStringParam("path", "")}'");

            var name = obj.name;
            Undo.DestroyObjectImmediate(obj);
            return McpResponse.Ok(req.Id, new Dictionary<string, object> { ["deleted"] = name });
        }

        public static McpResponse MoveObject(McpRequest req)
        {
            var obj = ResolveObject(req);
            if (obj == null)
                return McpResponse.Err(req.Id, $"Object not found: '{req.GetStringParam("path", "")}'");

            var parentPath = req.GetStringParam("parent", "");
            if (!string.IsNullOrEmpty(parentPath))
            {
                var parent = UnityMcpUtility.FindGameObject(parentPath);
                if (parent != null)
                    obj.transform.SetParent(parent.transform);
                else
                    return McpResponse.Err(req.Id, $"Parent not found: '{parentPath}'");
            }

            var t = obj.transform;
            var position = req.GetListParam("position");
            if (position.Count >= 3)
            {
                Undo.RecordObject(t, $"MCP Move {obj.name}");
                t.position = UnityMcpUtility.ToVector3(position, t.position);
            }

            var rotation = req.GetListParam("rotation");
            if (rotation.Count >= 3)
            {
                Undo.RecordObject(t, $"MCP Rotate {obj.name}");
                t.rotation = Quaternion.Euler(UnityMcpUtility.ToVector3(rotation, t.rotation.eulerAngles));
            }

            var scale = req.GetListParam("scale");
            if (scale.Count >= 3)
            {
                Undo.RecordObject(t, $"MCP Scale {obj.name}");
                t.localScale = UnityMcpUtility.ToVector3(scale, t.localScale);
            }

            return McpResponse.Ok(req.Id, new Dictionary<string, object>
            {
                ["name"] = obj.name,
                ["position"] = new List<object> { t.position.x, t.position.y, t.position.z },
                ["rotation"] = new List<object> { t.rotation.eulerAngles.x, t.rotation.eulerAngles.y, t.rotation.eulerAngles.z },
                ["scale"] = new List<object> { t.localScale.x, t.localScale.y, t.localScale.z }
            });
        }

        public static McpResponse DuplicateObject(McpRequest req)
        {
            var obj = ResolveObject(req);
            if (obj == null)
                return McpResponse.Err(req.Id, $"Object not found: '{req.GetStringParam("path", "")}'");

            var clone = Object.Instantiate(obj, obj.transform.parent);
            clone.name = req.GetStringParam("name", obj.name + " Copy");
            Undo.RegisterCreatedObjectUndo(clone, $"MCP Duplicate {obj.name}");
            Selection.activeGameObject = clone;
            return McpResponse.Ok(req.Id, SceneCommands.SerializeGameObject(clone));
        }

        public static McpResponse SetActive(McpRequest req)
        {
            var active = req.GetBoolParam("active", true);
            var obj = ResolveObject(req);
            if (obj == null)
                return McpResponse.Err(req.Id, $"Object not found: '{req.GetStringParam("path", "")}'");

            Undo.RecordObject(obj, $"MCP Set Active {obj.name}");
            obj.SetActive(active);
            return McpResponse.Ok(req.Id, new Dictionary<string, object> { ["path"] = UnityMcpUtility.GetHierarchyPath(obj), ["active"] = obj.activeSelf });
        }

        public static McpResponse AddComponent(McpRequest req)
        {
            var typeName = req.GetStringParam("component", req.GetStringParam("type", ""));
            if (string.IsNullOrWhiteSpace(typeName))
                return McpResponse.Err(req.Id, "No component type provided");

            var obj = ResolveObject(req);
            if (obj == null)
                return McpResponse.Err(req.Id, $"Object not found: '{req.GetStringParam("path", "")}'");

            var type = FindComponentType(typeName);
            if (type == null || !typeof(Component).IsAssignableFrom(type))
                return McpResponse.Err(req.Id, $"Component type not found: '{typeName}'");

            var component = Undo.AddComponent(obj, type);
            return McpResponse.Ok(req.Id, new Dictionary<string, object>
            {
                ["path"] = UnityMcpUtility.GetHierarchyPath(obj),
                ["component"] = component.GetType().Name
            });
        }

        public static McpResponse RemoveComponent(McpRequest req)
        {
            var componentName = req.GetStringParam("component", "");
            var obj = ResolveObject(req);
            if (obj == null)
                return McpResponse.Err(req.Id, $"Object not found: '{req.GetStringParam("path", "")}'");

            var component = PropertyCommands.FindComponent(obj, componentName);
            if (component == null || component is Transform)
                return McpResponse.Err(req.Id, $"Removable component not found: '{componentName}'");

            Undo.DestroyObjectImmediate(component);
            return McpResponse.Ok(req.Id, new Dictionary<string, object> { ["removed"] = componentName, ["path"] = UnityMcpUtility.GetHierarchyPath(obj) });
        }

        private static System.Type FindComponentType(string typeName)
        {
            foreach (var assembly in System.AppDomain.CurrentDomain.GetAssemblies())
            {
                var type = assembly.GetType(typeName) ?? assembly.GetType("UnityEngine." + typeName);
                if (type != null) return type;

                System.Type[] candidates;
                try
                {
                    candidates = assembly.GetTypes();
                }
                catch (System.Reflection.ReflectionTypeLoadException ex)
                {
                    candidates = ex.Types;
                }

                foreach (var candidate in candidates)
                {
                    if (candidate != null && candidate.Name.Equals(typeName, System.StringComparison.OrdinalIgnoreCase))
                        return candidate;
                }
            }
            return null;
        }
    }
}
