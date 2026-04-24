using System.Collections.Generic;
using System.IO;
using UnityEditor;

namespace GameEngineMCP
{
    public static class AssetCommands
    {
        public static McpResponse ListAssets(McpRequest req)
        {
            var path = UnityMcpUtility.NormalizeAssetPath(req.GetStringParam("path", "Assets"));
            var recursive = req.GetBoolParam("recursive", false);
            var filter = req.GetStringParam("filter", "");

            if (!AssetDatabase.IsValidFolder(path))
            {
                return McpResponse.Err(req.Id, $"Directory not found: '{path}'");
            }

            var assets = new List<Dictionary<string, object>>();
            var searchFolder = path;
            var guids = string.IsNullOrEmpty(filter)
                ? AssetDatabase.FindAssets("t:Object", new[] { searchFolder })
                : AssetDatabase.FindAssets(filter, new[] { searchFolder });

            var seen = new HashSet<string>();
            foreach (var guid in guids)
            {
                var assetPath = AssetDatabase.GUIDToAssetPath(guid);
                if (seen.Contains(assetPath)) continue;
                if (!recursive && Path.GetDirectoryName(assetPath)?.Replace('\\', '/') != searchFolder) continue;
                seen.Add(assetPath);

                assets.Add(SerializeAsset(assetPath));

                if (assets.Count >= 500) break; // Safety limit
            }

            return McpResponse.Ok(req.Id, new Dictionary<string, object>
            {
                ["assets"] = assets,
                ["count"] = assets.Count,
                ["path"] = searchFolder
            });
        }

        public static McpResponse GetAsset(McpRequest req)
        {
            var path = UnityMcpUtility.NormalizeAssetPath(req.GetStringParam("path", ""));
            if (string.IsNullOrWhiteSpace(path))
                return McpResponse.Err(req.Id, "No asset path provided");
            if (AssetDatabase.LoadMainAssetAtPath(path) == null && !AssetDatabase.IsValidFolder(path))
                return McpResponse.Err(req.Id, $"Asset not found: '{path}'");
            return McpResponse.Ok(req.Id, SerializeAsset(path));
        }

        public static McpResponse ImportAsset(McpRequest req)
        {
            var path = UnityMcpUtility.NormalizeAssetPath(req.GetStringParam("path", ""));
            if (string.IsNullOrWhiteSpace(path))
                return McpResponse.Err(req.Id, "No asset path provided");

            AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceUpdate);
            return McpResponse.Ok(req.Id, new Dictionary<string, object> { ["imported"] = path });
        }

        public static McpResponse RefreshAssets(McpRequest req)
        {
            AssetDatabase.Refresh(ImportAssetOptions.ForceUpdate);
            return McpResponse.Ok(req.Id, new Dictionary<string, object> { ["refreshed"] = true });
        }

        public static McpResponse CreateFolder(McpRequest req)
        {
            var parent = UnityMcpUtility.NormalizeAssetPath(req.GetStringParam("parent", "Assets"));
            var name = req.GetStringParam("name", "");
            if (string.IsNullOrWhiteSpace(name))
                return McpResponse.Err(req.Id, "No folder name provided");
            if (!AssetDatabase.IsValidFolder(parent))
                return McpResponse.Err(req.Id, $"Parent folder not found: '{parent}'");

            var guid = AssetDatabase.CreateFolder(parent, name);
            var path = AssetDatabase.GUIDToAssetPath(guid);
            return McpResponse.Ok(req.Id, new Dictionary<string, object> { ["path"] = path, ["guid"] = guid });
        }

        public static McpResponse DeleteAsset(McpRequest req)
        {
            var path = UnityMcpUtility.NormalizeAssetPath(req.GetStringParam("path", ""));
            if (string.IsNullOrWhiteSpace(path))
                return McpResponse.Err(req.Id, "No asset path provided");

            var deleted = AssetDatabase.DeleteAsset(path);
            return McpResponse.Ok(req.Id, new Dictionary<string, object> { ["deleted"] = deleted, ["path"] = path });
        }

        public static McpResponse MoveAsset(McpRequest req)
        {
            var from = UnityMcpUtility.NormalizeAssetPath(req.GetStringParam("from", req.GetStringParam("path", "")));
            var to = UnityMcpUtility.NormalizeAssetPath(req.GetStringParam("to", ""));
            if (string.IsNullOrWhiteSpace(from) || string.IsNullOrWhiteSpace(to))
                return McpResponse.Err(req.Id, "Both from/path and to are required");

            var error = AssetDatabase.MoveAsset(from, to);
            if (!string.IsNullOrEmpty(error))
                return McpResponse.Err(req.Id, error);
            return McpResponse.Ok(req.Id, new Dictionary<string, object> { ["from"] = from, ["to"] = to });
        }

        public static McpResponse CopyAsset(McpRequest req)
        {
            var from = UnityMcpUtility.NormalizeAssetPath(req.GetStringParam("from", req.GetStringParam("path", "")));
            var to = UnityMcpUtility.NormalizeAssetPath(req.GetStringParam("to", ""));
            if (string.IsNullOrWhiteSpace(from) || string.IsNullOrWhiteSpace(to))
                return McpResponse.Err(req.Id, "Both from/path and to are required");

            var copied = AssetDatabase.CopyAsset(from, to);
            return McpResponse.Ok(req.Id, new Dictionary<string, object> { ["copied"] = copied, ["from"] = from, ["to"] = to });
        }

        public static McpResponse RenameAsset(McpRequest req)
        {
            var path = UnityMcpUtility.NormalizeAssetPath(req.GetStringParam("path", ""));
            var name = req.GetStringParam("name", "");
            if (string.IsNullOrWhiteSpace(path) || string.IsNullOrWhiteSpace(name))
                return McpResponse.Err(req.Id, "Both path and name are required");

            var error = AssetDatabase.RenameAsset(path, name);
            if (!string.IsNullOrEmpty(error))
                return McpResponse.Err(req.Id, error);
            return McpResponse.Ok(req.Id, new Dictionary<string, object> { ["path"] = path, ["name"] = name });
        }

        public static McpResponse GetDependencies(McpRequest req)
        {
            var path = UnityMcpUtility.NormalizeAssetPath(req.GetStringParam("path", ""));
            var recursive = req.GetBoolParam("recursive", true);
            var dependencies = AssetDatabase.GetDependencies(path, recursive);
            return McpResponse.Ok(req.Id, new Dictionary<string, object>
            {
                ["path"] = path,
                ["dependencies"] = new List<string>(dependencies),
                ["count"] = dependencies.Length
            });
        }

        public static McpResponse RevealAsset(McpRequest req)
        {
            var path = UnityMcpUtility.NormalizeAssetPath(req.GetStringParam("path", ""));
            var obj = AssetDatabase.LoadMainAssetAtPath(path);
            if (obj == null)
                return McpResponse.Err(req.Id, $"Asset not found: '{path}'");

            EditorUtility.FocusProjectWindow();
            Selection.activeObject = obj;
            EditorGUIUtility.PingObject(obj);
            return McpResponse.Ok(req.Id, new Dictionary<string, object> { ["revealed"] = path });
        }

        private static Dictionary<string, object> SerializeAsset(string assetPath)
        {
            var type = AssetDatabase.GetMainAssetTypeAtPath(assetPath);
            var guid = AssetDatabase.AssetPathToGUID(assetPath);
            var asset = AssetDatabase.LoadMainAssetAtPath(assetPath);
            return new Dictionary<string, object>
            {
                ["name"] = Path.GetFileNameWithoutExtension(assetPath),
                ["path"] = assetPath,
                ["guid"] = guid,
                ["type"] = AssetDatabase.IsValidFolder(assetPath) ? "Folder" : type?.Name ?? "Unknown",
                ["extension"] = Path.GetExtension(assetPath).TrimStart('.'),
                ["labels"] = asset != null ? new List<string>(AssetDatabase.GetLabels(asset)) : new List<string>()
            };
        }
    }
}
