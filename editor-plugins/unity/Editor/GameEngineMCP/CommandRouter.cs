using System.Collections.Generic;

namespace GameEngineMCP
{
    /// <summary>
    /// Routes incoming MCP commands to the appropriate handler.
    /// All handlers run on the main Unity thread via EditorApplication.delayCall.
    /// </summary>
    public static class CommandRouter
    {
        public static McpResponse Route(McpRequest request)
        {
            try
            {
                return request.Command switch
                {
                    "ping" => EditorCommands.Ping(request),
                    "get_editor_info" => EditorCommands.GetEditorInfo(request),
                    "play" => EditorCommands.Play(request),
                    "pause" => EditorCommands.Pause(request),
                    "stop" => EditorCommands.Stop(request),
                    "get_console_logs" => ConsoleCommands.GetConsoleLogs(request),
                    "clear_console" => ConsoleCommands.ClearConsole(request),
                    "get_scene_hierarchy" => SceneCommands.GetSceneHierarchy(request),
                    "get_active_scene" => SceneCommands.GetActiveScene(request),
                    "save_scene" => SceneCommands.SaveScene(request),
                    "get_object" => ObjectCommands.GetObject(request),
                    "create_object" => ObjectCommands.CreateObject(request),
                    "delete_object" => ObjectCommands.DeleteObject(request),
                    "move_object" => ObjectCommands.MoveObject(request),
                    "get_properties" => PropertyCommands.GetProperties(request),
                    "set_property" => PropertyCommands.SetProperty(request),
                    "set_properties" => PropertyCommands.SetProperties(request),
                    "list_assets" => AssetCommands.ListAssets(request),
                    "take_screenshot" => ScreenshotCommands.TakeScreenshot(request),
                    "execute_code" => CodeCommands.ExecuteCode(request),
                    "run_tests" => EditorCommands.RunTests(request),
                    _ => McpResponse.Err(request.Id, $"Unknown command: {request.Command}")
                };
            }
            catch (System.Exception ex)
            {
                return McpResponse.Err(request.Id, $"Command '{request.Command}' failed: {ex.Message}");
            }
        }
    }
}
