using System.Collections.Generic;
using System.Reflection;
using UnityEditor;
using UnityEngine;

namespace GameEngineMCP
{
    public static class PropertyCommands
    {
        public static McpResponse GetProperties(McpRequest req)
        {
            var path = req.GetStringParam("path", "");
            var componentName = req.GetStringParam("component", "");
            var obj = GameObject.Find(path);

            if (obj == null)
            {
                return McpResponse.Err(req.Id, $"Object not found: '{path}'");
            }

            var result = new Dictionary<string, object>();

            if (!string.IsNullOrEmpty(componentName))
            {
                var comp = FindComponent(obj, componentName);
                if (comp == null)
                    return McpResponse.Err(req.Id, $"Component '{componentName}' not found on '{path}'");

                result["properties"] = SerializeComponentProperties(comp);
                result["component"] = comp.GetType().Name;
            }
            else
            {
                // Return all components and their properties
                var components = new List<Dictionary<string, object>>();
                foreach (var comp in obj.GetComponents<Component>())
                {
                    if (comp == null) continue;
                    components.Add(new Dictionary<string, object>
                    {
                        ["name"] = comp.GetType().Name,
                        ["properties"] = SerializeComponentProperties(comp)
                    });
                }
                result["components"] = components;
            }

            return McpResponse.Ok(req.Id, result);
        }

        public static McpResponse SetProperty(McpRequest req)
        {
            var path = req.GetStringParam("path", "");
            var componentName = req.GetStringParam("component", "");
            var propertyName = req.GetStringParam("property", "");
            var value = req.Params != null && req.Params.ContainsKey("value") ? req.Params["value"] : null;

            var obj = GameObject.Find(path);
            if (obj == null)
                return McpResponse.Err(req.Id, $"Object not found: '{path}'");

            var comp = FindComponent(obj, componentName);
            if (comp == null)
                return McpResponse.Err(req.Id, $"Component '{componentName}' not found on '{path}'");

            // Try SerializedObject approach first (works with Unity built-in components)
            var so = new SerializedObject(comp);
            var prop = so.FindProperty(propertyName);

            if (prop != null)
            {
                if (!ApplySerializedProperty(prop, value))
                    return McpResponse.Err(req.Id, $"Cannot set property type for '{propertyName}'");

                so.ApplyModifiedProperties();
                return McpResponse.Ok(req.Id, new Dictionary<string, object>
                {
                    ["path"] = path,
                    ["component"] = componentName,
                    ["property"] = propertyName,
                    ["value"] = value
                });
            }

            // Fallback: reflection
            var field = comp.GetType().GetField(propertyName,
                BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
            if (field != null)
            {
                var converted = ConvertValue(value, field.FieldType);
                field.SetValue(comp, converted);
                return McpResponse.Ok(req.Id, new Dictionary<string, object>
                {
                    ["path"] = path,
                    ["component"] = componentName,
                    ["property"] = propertyName,
                    ["value"] = value
                });
            }

            var property = comp.GetType().GetProperty(propertyName,
                BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
            if (property != null && property.CanWrite)
            {
                var converted = ConvertValue(value, property.PropertyType);
                property.SetValue(comp, converted);
                return McpResponse.Ok(req.Id, new Dictionary<string, object>
                {
                    ["path"] = path,
                    ["component"] = componentName,
                    ["property"] = propertyName,
                    ["value"] = value
                });
            }

            return McpResponse.Err(req.Id, $"Property '{propertyName}' not found on '{componentName}'");
        }

        public static McpResponse SetProperties(McpRequest req)
        {
            var path = req.GetStringParam("path", "");
            var componentName = req.GetStringParam("component", "");
            var properties = req.GetDictParam("properties");

            var obj = GameObject.Find(path);
            if (obj == null)
                return McpResponse.Err(req.Id, $"Object not found: '{path}'");

            var comp = FindComponent(obj, componentName);
            if (comp == null)
                return McpResponse.Err(req.Id, $"Component '{componentName}' not found on '{path}'");

            var so = new SerializedObject(comp);
            var set = new List<string>();
            var failed = new List<string>();

            foreach (var kvp in properties)
            {
                var prop = so.FindProperty(kvp.Key);
                if (prop != null && ApplySerializedProperty(prop, kvp.Value))
                {
                    set.Add(kvp.Key);
                }
                else
                {
                    // Reflection fallback
                    var field = comp.GetType().GetField(kvp.Key,
                        BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
                    if (field != null)
                    {
                        field.SetValue(comp, ConvertValue(kvp.Value, field.FieldType));
                        set.Add(kvp.Key);
                    }
                    else
                    {
                        failed.Add(kvp.Key);
                    }
                }
            }

            so.ApplyModifiedProperties();

            return McpResponse.Ok(req.Id, new Dictionary<string, object>
            {
                ["set"] = set,
                ["failed"] = failed
            });
        }

        // --- Helpers ---

        private static Component FindComponent(GameObject obj, string name)
        {
            foreach (var comp in obj.GetComponents<Component>())
            {
                if (comp == null) continue;
                if (comp.GetType().Name.Equals(name, System.StringComparison.OrdinalIgnoreCase))
                    return comp;
            }

            // Try partial match
            foreach (var comp in obj.GetComponents<Component>())
            {
                if (comp == null) continue;
                if (comp.GetType().Name.IndexOf(name, System.StringComparison.OrdinalIgnoreCase) >= 0)
                    return comp;
            }

            return null;
        }

        private static Dictionary<string, object> SerializeComponentProperties(Component comp)
        {
            var props = new Dictionary<string, object>();
            var so = new SerializedObject(comp);
            var prop = so.GetIterator();

            if (prop.NextVisible(true))
            {
                do
                {
                    props[prop.name] = PropertyValueToString(prop);
                }
                while (prop.NextVisible(false));
            }

            return props;
        }

        private static object PropertyValueToString(SerializedProperty prop)
        {
            switch (prop.propertyType)
            {
                case SerializedPropertyType.Integer:
                    return prop.intValue;
                case SerializedPropertyType.Boolean:
                    return prop.boolValue;
                case SerializedPropertyType.Float:
                    return prop.floatValue;
                case SerializedPropertyType.String:
                    return prop.stringValue;
                case SerializedPropertyType.Color:
                    var c = prop.colorValue;
                    return $"#{ColorUtility.ToHtmlStringRGBA(c)}";
                case SerializedPropertyType.Vector3:
                    return new List<object> { prop.vector3Value.x, prop.vector3Value.y, prop.vector3Value.z };
                case SerializedPropertyType.Vector2:
                    return new List<object> { prop.vector2Value.x, prop.vector2Value.y };
                case SerializedPropertyType.Quaternion:
                    var e = prop.quaternionValue.eulerAngles;
                    return new List<object> { e.x, e.y, e.z };
                case SerializedPropertyType.Enum:
                    return prop.enumNames[prop.enumValueIndex];
                case SerializedPropertyType.LayerMask:
                    return prop.intValue;
                case SerializedPropertyType.ObjectReference:
                    return prop.objectReferenceValue != null ? prop.objectReferenceValue.name : null;
                default:
                    return prop.propertyType.ToString();
            }
        }

        private static bool ApplySerializedProperty(SerializedProperty prop, object value)
        {
            try
            {
                switch (prop.propertyType)
                {
                    case SerializedPropertyType.Integer:
                        prop.intValue = System.Convert.ToInt32(value);
                        return true;
                    case SerializedPropertyType.Boolean:
                        prop.boolValue = System.Convert.ToBoolean(value);
                        return true;
                    case SerializedPropertyType.Float:
                        prop.floatValue = System.Convert.ToSingle(value);
                        return true;
                    case SerializedPropertyType.String:
                        prop.stringValue = value?.ToString() ?? "";
                        return true;
                    case SerializedPropertyType.Enum:
                        if (value is string enumStr)
                        {
                            var idx = System.Array.IndexOf(prop.enumNames, enumStr);
                            if (idx >= 0) { prop.enumValueIndex = idx; return true; }
                        }
                        prop.enumValueIndex = System.Convert.ToInt32(value);
                        return true;
                    default:
                        return false;
                }
            }
            catch
            {
                return false;
            }
        }

        private static object ConvertValue(object value, System.Type targetType)
        {
            if (value == null) return null;

            if (targetType == typeof(float))
                return System.Convert.ToSingle(value);
            if (targetType == typeof(int))
                return System.Convert.ToInt32(value);
            if (targetType == typeof(bool))
                return System.Convert.ToBoolean(value);
            if (targetType == typeof(string))
                return value.ToString();
            if (targetType == typeof(Vector3) && value is List<object> v3 && v3.Count >= 3)
                return new Vector3((float)(double)v3[0], (float)(double)v3[1], (float)(double)v3[2]);
            if (targetType == typeof(Vector2) && value is List<object> v2 && v2.Count >= 2)
                return new Vector2((float)(double)v2[0], (float)(double)v2[1]);

            return System.Convert.ChangeType(value, targetType);
        }
    }
}
