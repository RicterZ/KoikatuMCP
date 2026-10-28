## MMDD extension dependencies and timeout diagnosis

The HTTP MCP server and the game plugin must be updated together. Seeing 30 MCP tools proves only the HTTP server has the new code. The upstream KKStudioSocket 1.0.0 does not handle `type: mmdd`; it can answer ping while MMDD requests receive no response and time out after 5000 ms. Increasing the timeout does not add the missing handler.

This extension requires:

- The custom `KK_KKStudioSocket.dll` 1.1.0.0 from `game-plugin`, installed into the game's `BepInEx/plugins` after saving and closing CharaStudio. Confirm `Loading [KKStudioSocket 1.1.0]` in `BepInEx/LogOutput.log` after launch. Restarting only the HTTP server is insufficient.
- The verified KK environment: BepInEx 5.4.23.2, KKAPI 1.42.2, and the existing websocket-sharp/Newtonsoft.Json libraries. Do not replace these dependencies or the entire BepInEx folder blindly.
- VNGE 42.9 / MMDD 2.9.4, with its existing Unity.Console 1.0.1.0, IronPython, Microsoft.Scripting, Microsoft.Scripting.Core, Microsoft.Dynamic and StdLib installation intact. The bridge compiles against the installed Console scripting DLLs and uses that Console's live engine, not an independent Python installation. No pip packages or extra Python installation are required.
- VNGE initialized in Studio and MMD Director opened before invoking MMDD tools. If initialization is missing, the new plugin should return a descriptive error instead of a success response.

Implementation: `extensions/KKStudioSocket/src/KKStudioSocket.Core/KKStudioSocketPlugin.cs` queues `mmdd` requests on the Unity main thread. `Commands/MmddCommandHandler.cs` obtains the existing `Unity.Console.Program.MainEngine` through reflection, following the installed VNGE C# example, then executes the fixed embedded `Bridge/mmdd_mcp_bridge.py` in a separate scope. JSON is passed as a variable, not injected as code. The adapter uses `vnge_game.gdata.mmdd` and the real MMDD `stop`, `gotoFrame`, `update`, `start`, and VmdLib camera methods. It does not use VMDPlayPlugin as a substitute.

If ping works but MMDD times out, first inspect the loaded plugin version and game log. If it is already 1.1.0, inspect Studio main-thread responsiveness and the game-side exception; HTTP status 200 alone does not prove a tool succeeded. The tool's returned content must also be checked.
