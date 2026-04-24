using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;

namespace GameEngineMCP
{
    public static class AssetCommands
    {
        public static McpResponse ListAssets(McpRequest req)
        {
            var path = req.GetStringParam("path", "Assets");
            var recursive = req.GetBoolParam("recursive", false);
            var filter = req.GetStringParam("filter", "");

            if (!Directory.Exists(path))
            {
                return McpResponse.Err(req.Id, $"Directory not found: '{path}'");
            }

            var assets = new List<Dictionary<string, object>>();
            var searchOption = recursive ? SearchOption.AllDirectories : SearchOption.TopDirectoryOnly;

            var searchFolder = path;
            if (!searchFolder.StartsWith("Assets"))
            {
                // Try prepending Assets
                if (Directory.Exists(Path.Combine("Assets", path)))
                    searchFolder = Path.Combine("Assets", path);
            }

            var guids = string.IsNullOrEmpty(filter)
                ? AssetDatabase.FindAssets("t:Object", new[] { searchFolder })
                : AssetDatabase.FindAssets(filter, new[] { searchFolder });

            var seen = new HashSet<string>();
            foreach (var guid in guids)
            {
                var assetPath = AssetDatabase.GUIDToAssetPath(guid);
                if (seen.Contains(assetPath)) continue;
                seen.Add(assetPath);

                var type = AssetDatabase.GetMainAssetTypeAtPath(assetPath);
                assets.Add(new Dictionary<string, object>
                {
                    ["name"] = Path.GetFileNameWithoutExtension(assetPath),
                    ["path"] = assetPath,
                    ["type"] = type?.Name ?? "Unknown",
                    ["extension"] = Path.GetExtension(assetPath).TrimStart('.')
                });

                if (assets.Count >= 500) break; // Safety limit
            }

            return McpResponse.Ok(req.Id, new Dictionary<string, object>
            {
                ["assets"] = assets,
                ["count"] = assets.Count,
                ["path"] = searchFolder
            });
        }
    }
}
