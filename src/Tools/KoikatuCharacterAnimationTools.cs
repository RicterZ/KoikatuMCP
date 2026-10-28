using System.ComponentModel;
using System.Text.Json;
using KoikatuMCP.Services;
using KKStudioSocket.Models.Requests;
using ModelContextProtocol.Server;

namespace KoikatuMCP.Tools;

[McpServerToolType]
public static class KoikatuCharacterAnimationTools
{
    [McpServerTool, Description("List installed CharaStudio built-in animations with real names and group/category/no. IDs are local to this running game; query again after mods change. Requires custom KKStudioSocket 1.2.1 and initialized VNGE 42.9.")]
    public static Task<string> CharacterAnimationList(WebSocketService webSocketService,
        string? search = null, int? group = null, int? category = null, int offset = 0, int limit = 50,
        [Description("Rebuild the cached installed catalog after game/MOD/mapping changes")] bool refresh = false) =>
        Send(webSocketService, new CharacterAnimationCommand {
            type = "character_animation", command = "list", search = search,
            group = group, category = category, offset = offset, limit = limit, refresh = refresh });

    [McpServerTool, Description("Read a character's built-in animation, speed, Animator time, IK/FK and MMDD bone-control state. characterId is the ID from the Studio scene tree.")]
    public static Task<string> CharacterAnimationGet(WebSocketService webSocketService, int characterId) =>
        Send(webSocketService, new CharacterAnimationCommand {
            type = "character_animation", command = "get", characterId = characterId });

    [McpServerTool, Description("Switch a character to an installed built-in animation, wait for its controller, and verify evaluated normalized time 0. First acquire mode=builtin using character_animation_control. MMDD must remain paused. No character translation is applied; walking may be in place.")]
    public static Task<string> CharacterAnimationSet(WebSocketService webSocketService, int characterId,
        int group, int category, int no, float speed = 1) =>
        Send(webSocketService, new CharacterAnimationCommand {
            type = "character_animation", command = "set", characterId = characterId,
            group = group, category = category, no = no, speed = speed });

    [McpServerTool, Description("mode=builtin snapshots animation/speed and IK/FK, disables only this character's MMDD bone controllers and IK/FK. mode=restore restores that snapshot, preserving tracks and camera keys. MMDD must be paused. Restore before saving/reloading scenes or closing Studio; snapshots are memory-only.")]
    public static Task<string> CharacterAnimationControl(WebSocketService webSocketService,
        int characterId, string mode) =>
        Send(webSocketService, new CharacterAnimationCommand {
            type = "character_animation", command = "control", characterId = characterId, mode = mode });

    private static async Task<string> Send(WebSocketService service, CharacterAnimationCommand request)
    {
        try
        {
            return await service.SendRequestAsync<CharacterAnimationCommand, string>(request, 10000)
                ?? JsonSerializer.Serialize(new { type = "error", message = "Empty animation response." });
        }
        catch (Exception ex)
        {
            return JsonSerializer.Serialize(new { type = "error", message = ex.Message });
        }
    }
}
