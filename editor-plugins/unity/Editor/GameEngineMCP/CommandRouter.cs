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
                    "execute_menu_item" => EditorCommands.ExecuteMenuItem(request),
                    "repaint_editor" => EditorCommands.Repaint(request),
                    "get_selection" => EditorCommands.GetSelection(request),
                    "set_selection" => EditorCommands.SetSelection(request),
                    "ping_object" => EditorCommands.PingObject(request),
                    "get_console_logs" => ConsoleCommands.GetConsoleLogs(request),
                    "clear_console" => ConsoleCommands.ClearConsole(request),
                    "new_scene" => SceneCommands.NewScene(request),
                    "open_scene" => SceneCommands.OpenScene(request),
                    "close_scene" => SceneCommands.CloseScene(request),
                    "get_scene_hierarchy" => SceneCommands.GetSceneHierarchy(request),
                    "get_active_scene" => SceneCommands.GetActiveScene(request),
                    "get_open_scenes" => SceneCommands.GetOpenScenes(request),
                    "save_scene" => SceneCommands.SaveScene(request),
                    "save_all_scenes" => SceneCommands.SaveAllScenes(request),
                    "mark_scene_dirty" => SceneCommands.MarkSceneDirty(request),
                    "get_object" => ObjectCommands.GetObject(request),
                    "create_object" => ObjectCommands.CreateObject(request),
                    "delete_object" => ObjectCommands.DeleteObject(request),
                    "move_object" => ObjectCommands.MoveObject(request),
                    "duplicate_object" => ObjectCommands.DuplicateObject(request),
                    "set_object_active" => ObjectCommands.SetActive(request),
                    "add_component" => ObjectCommands.AddComponent(request),
                    "remove_component" => ObjectCommands.RemoveComponent(request),
                    "get_properties" => PropertyCommands.GetProperties(request),
                    "set_property" => PropertyCommands.SetProperty(request),
                    "set_properties" => PropertyCommands.SetProperties(request),
                    "list_assets" => AssetCommands.ListAssets(request),
                    "get_asset" => AssetCommands.GetAsset(request),
                    "import_asset" => AssetCommands.ImportAsset(request),
                    "refresh_assets" => AssetCommands.RefreshAssets(request),
                    "create_folder" => AssetCommands.CreateFolder(request),
                    "delete_asset" => AssetCommands.DeleteAsset(request),
                    "move_asset" => AssetCommands.MoveAsset(request),
                    "copy_asset" => AssetCommands.CopyAsset(request),
                    "rename_asset" => AssetCommands.RenameAsset(request),
                    "get_asset_dependencies" => AssetCommands.GetDependencies(request),
                    "reveal_asset" => AssetCommands.RevealAsset(request),
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
