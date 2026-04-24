using UnityEditor;
using UnityEngine;

namespace GameEngineMCP
{
    public static class ScreenshotCommands
    {
        public static McpResponse TakeScreenshot(McpRequest req)
        {
            var width = req.GetIntParam("width", 0);
            var height = req.GetIntParam("height", 0);

            // Use Game view size if not specified
            var gameView = GetGameView();
            if (gameView != null)
            {
                var gvSize = gameView.position.size;
                if (width <= 0) width = (int)gvSize.x;
                if (height <= 0) height = (int)gvSize.y;
            }

            if (width <= 0) width = Screen.width;
            if (height <= 0) height = Screen.height;

            // Capture the game view render
            var tempRT = RenderTexture.GetTemporary(width, height, 24);
            var prevRT = RenderTexture.active;
            RenderTexture.active = tempRT;

            var cameras = Camera.allCameras;
            foreach (var cam in cameras)
            {
                if (!cam.gameObject.activeInHierarchy) continue;
                var prevTarget = cam.targetTexture;
                cam.targetTexture = tempRT;
                cam.Render();
                cam.targetTexture = prevTarget;
            }

            var tex = new Texture2D(width, height, TextureFormat.RGB24, false);
            tex.ReadPixels(new Rect(0, 0, width, height), 0, 0);
            tex.Apply();

            RenderTexture.active = prevRT;
            RenderTexture.ReleaseTemporary(tempRT);

            var pngBytes = tex.EncodeToPNG();
            var base64 = System.Convert.ToBase64String(pngBytes);

            Object.DestroyImmediate(tex);

            return McpResponse.Ok(req.Id, new Dictionary<string, object>
            {
                ["image_base64"] = base64,
                ["width"] = width,
                ["height"] = height,
                ["format"] = "png"
            });
        }

        private static EditorWindow GetGameView()
        {
            var assembly = System.Reflection.Assembly.GetAssembly(typeof(EditorWindow));
            var gameViewType = assembly.GetType("UnityEditor.GameView");
            if (gameViewType == null) return null;

            // Use FindObjectOfType to locate an existing GameView without creating one.
            return UnityEngine.Object.FindObjectOfType(gameViewType) as EditorWindow;
        }
    }
}
