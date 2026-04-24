using System;
using System.Collections.Generic;
using System.IO;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEngine;

namespace GameEngineMCP
{
    internal static class UnityMcpUtility
    {
        public static GameObject FindGameObject(string path, int instanceId = -1)
        {
            if (instanceId > 0)
            {
                var byId = EditorUtility.InstanceIDToObject(instanceId) as GameObject;
                if (byId != null) return byId;
            }

            if (string.IsNullOrWhiteSpace(path)) return null;

            var direct = GameObject.Find(path);
            if (direct != null) return direct;

            var normalized = path.Trim('/');
            var all = Resources.FindObjectsOfTypeAll<GameObject>();
            foreach (var go in all)
            {
                if (go == null || EditorUtility.IsPersistent(go)) continue;
                if (GetHierarchyPath(go) == normalized || go.name == normalized)
                    return go;
            }

            return null;
        }

        public static string GetHierarchyPath(GameObject obj)
        {
            if (obj == null) return "";
            var names = new Stack<string>();
            var current = obj.transform;
            while (current != null)
            {
                names.Push(current.name);
                current = current.parent;
            }
            return string.Join("/", names.ToArray());
        }

        public static string NormalizeAssetPath(string path, string fallback = "Assets")
        {
            if (string.IsNullOrWhiteSpace(path)) return fallback;
            path = path.Replace('\\', '/').Trim();
            if (path.StartsWith(Application.dataPath, StringComparison.OrdinalIgnoreCase))
                return "Assets" + path.Substring(Application.dataPath.Length);
            if (path.StartsWith("Assets", StringComparison.OrdinalIgnoreCase) ||
                path.StartsWith("Packages", StringComparison.OrdinalIgnoreCase))
                return path;
            return Path.Combine("Assets", path).Replace('\\', '/');
        }

        public static List<object> ToList(object value)
        {
            if (value is List<object> list) return list;
            if (value is JArray arr) return arr.ToObject<List<object>>() ?? new List<object>();
            return new List<object>();
        }

        public static Dictionary<string, object> ToDictionary(object value)
        {
            if (value is Dictionary<string, object> dict) return dict;
            if (value is JObject obj) return obj.ToObject<Dictionary<string, object>>() ?? new Dictionary<string, object>();
            return new Dictionary<string, object>();
        }

        public static Vector3 ToVector3(IList<object> values, Vector3 fallback)
        {
            if (values == null || values.Count < 3) return fallback;
            return new Vector3(Convert.ToSingle(values[0]), Convert.ToSingle(values[1]), Convert.ToSingle(values[2]));
        }

        public static Vector2 ToVector2(IList<object> values, Vector2 fallback)
        {
            if (values == null || values.Count < 2) return fallback;
            return new Vector2(Convert.ToSingle(values[0]), Convert.ToSingle(values[1]));
        }

        public static Dictionary<string, object> SerializeUnityObject(UnityEngine.Object obj)
        {
            if (obj == null) return null;
            var path = AssetDatabase.GetAssetPath(obj);
            return new Dictionary<string, object>
            {
                ["name"] = obj.name,
                ["type"] = obj.GetType().Name,
                ["instanceId"] = obj.GetInstanceID(),
                ["path"] = path ?? ""
            };
        }
    }
}
