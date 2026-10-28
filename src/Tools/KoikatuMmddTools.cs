using System.ComponentModel;
using System.Text.Json;
using KoikatuMCP.Services;
using KKStudioSocket.Models.Requests;
using ModelContextProtocol.Server;

namespace KoikatuMCP.Tools;

[McpServerToolType]
public static class KoikatuMmddTools
{
    [McpServerTool, Description("Read VNGE/MMD Director readiness, playback state, frame and camera tracks. Requires the MMDD-enabled KKStudioSocket plugin.")]
    public static Task<string> MmddStatus(WebSocketService webSocketService) =>
        Send(webSocketService, "status");

    [McpServerTool, Description("Pause MMD Director and return its actual playback state and frame.")]
    public static Task<string> MmddPause(WebSocketService webSocketService) =>
        Send(webSocketService, "pause");

    [McpServerTool, Description("Pause MMD Director, seek to a frame, evaluate its controllers and return the actual frame. This does not guarantee a rendered screenshot has completed.")]
    public static Task<string> MmddSeek(
        WebSocketService webSocketService,
        [Description("Non-negative MMDD frame number")] int frame) =>
        Send(webSocketService, "seek", frame: frame);

    [McpServerTool, Description("Start MMD Director playback from its current position and return the actual playback state.")]
    public static Task<string> MmddPlay(WebSocketService webSocketService) =>
        Send(webSocketService, "play");

    [McpServerTool, Description("Load and activate a camera VMD in MMD Director. Existing camera tracks are retained. The path must be an absolute .vmd path on the game host.")]
    public static Task<string> MmddLoadCamera(
        WebSocketService webSocketService,
        [Description("Absolute camera .vmd path on the game host")] string path) =>
        Send(webSocketService, "load_camera", path: path, timeoutMs: 30000);

    [McpServerTool, Description("Record the current Studio camera as a camera keyframe in MMD Director. An existing keyframe at that frame is replaced. Pause MMDD, then set the desired view before calling.")]
    public static Task<string> MmddRecordCamera(
        WebSocketService webSocketService,
        [Description("Non-negative frame number for the camera keyframe")] int frame,
        [Description("Optional zero-based MMDD camera track index; otherwise use the active main camera track")] int? cameraIndex = null) =>
        Send(webSocketService, "record_camera", frame: frame, cameraIndex: cameraIndex);

    [McpServerTool, Description("Export an MMD Director camera track to a new .vmd file on the game host. Existing files are not overwritten.")]
    public static Task<string> MmddExportCamera(
        WebSocketService webSocketService,
        [Description("Absolute output .vmd path on the game host")] string path,
        [Description("Optional zero-based MMDD camera track index; otherwise use the active main camera track")] int? cameraIndex = null) =>
        Send(webSocketService, "export_camera", path: path, cameraIndex: cameraIndex, timeoutMs: 30000);

    private static async Task<string> Send(
        WebSocketService service, string command, int? frame = null, string? path = null,
        int? cameraIndex = null, int timeoutMs = 5000)
    {
        try
        {
            if (frame < 0)
                throw new ArgumentOutOfRangeException(nameof(frame), "Frame must be non-negative.");
            if (cameraIndex < 0)
                throw new ArgumentOutOfRangeException(nameof(cameraIndex), "Camera index must be non-negative.");
            if (command is "load_camera" or "export_camera")
            {
                if (string.IsNullOrWhiteSpace(path) || !Path.IsPathFullyQualified(path) ||
                    !string.Equals(Path.GetExtension(path), ".vmd", StringComparison.OrdinalIgnoreCase))
                    throw new ArgumentException("Path must be an absolute .vmd path on the game host.", nameof(path));
            }

            var request = new MmddCommand
            {
                type = "mmdd",
                command = command,
                frame = frame,
                path = path,
                cameraIndex = cameraIndex
            };
            return await service.SendRequestAsync<MmddCommand, string>(request, timeoutMs)
                ?? JsonSerializer.Serialize(new { type = "error", message = "Empty MMDD response." });
        }
        catch (Exception ex)
        {
            return JsonSerializer.Serialize(new { type = "error", message = ex.Message });
        }
    }
}
