# KoikatuMCP — paired Windows HTTP edition

Control KK CharaStudio through MCP: scene objects, characters, transforms, screenshots, built-in character animations and VNGE MMD Director (MMDD).

This fork has **two running components**, distributed together:

```text
MCP client → HTTP :8766 → KoikatuMCP.exe → WebSocket :8765 → KK_KKStudioSocket.dll → CharaStudio
```

- **KoikatuMCP.exe** runs outside the game and serves Streamable HTTP MCP.
- **KK_KKStudioSocket.dll** is a BepInEx plugin loaded inside CharaStudio. The EXE cannot control the game without it.

The components have separate upstream forks: [MCP server](https://github.com/RicterZ/KoikatuMCP) (MIT) and [game plugin](https://github.com/RicterZ/KKStudioSocket) (GPL-3.0). This repository vendors the paired plugin source in `extensions/KKStudioSocket` for one-command builds. See [source provenance](SOURCE-PROVENANCE.md). Each component retains its license; bundling does not relicense the plugin as MIT.

## Install the paired package

Download the Windows paired ZIP from [Releases](https://github.com/RicterZ/KoikatuMCP/releases). It contains the self-contained `KoikatuMCP.exe`, `game-plugin/KK_KKStudioSocket.dll`, installer, source/build information, licenses and cache utilities. The game, character cards, MODs, VNGE and their dependencies are **not included**.

1. Use an existing working **KK CharaStudio** installation with BepInEx, KKAPI, websocket-sharp and Newtonsoft.Json. Verified installed versions: BepInEx 5.4.23.2, KKAPI 1.42.2. KKS is not validated by this fork.
2. Save your scene and close CharaStudio. Extract the ZIP to a separate directory. In PowerShell run:

   ```powershell
   .\Install-MMDDPlugin.ps1 -GameDir 'C:\Games\Koikatu'
   ```

   Substitute your actual game directory. The installer checks CharaStudio is closed, backs up an existing DLL, and installs only the Socket plugin. It does not install/replace the entire BepInEx folder.
3. Start Studio. Check `BepInEx/LogOutput.log` contains `Loading [KKStudioSocket 1.2.1]`. An old loaded DLL is not updated by restarting the EXE.
4. Start `KoikatuMCP.exe`. No separate .NET runtime is required for the paired self-contained Windows EXE. The default listener is **`http://0.0.0.0:8766/`**; connect a Streamable HTTP MCP client to `http://127.0.0.1:8766/`. For another machine, use the server machine's LAN IP. Keep this unauthenticated endpoint on a trusted network; it controls scene objects and reads host-side paths. The game WebSocket stays loopback-only by default.

   To bind HTTP only to localhost:

   ```powershell
   $env:KOIKATUMCP_URL = 'http://127.0.0.1:8766'
   .\KoikatuMCP.exe
   ```

   `KKSTUDIOSOCKET_URL` overrides the EXE's game connection (default `ws://127.0.0.1:8765/ws`). Stop the EXE with Ctrl+C. File logs are written beside it as `koikatu-mcp-YYYYMMDD.log`.
5. Refresh the MCP client's tools. Expect 34 tools. Check `ping`, then `tree` before changing the scene.

### Optional VNGE/MMDD dependencies

The original scene tools do not require VNGE. The character-animation bridge requires initialized **VNGE 42.9**; the MMDD tools additionally require **MMD Director 2.9.4** opened through VNGE → Utilities → MMD Director. Keep the existing Unity.Console 1.0.1.0, IronPython, Microsoft.Scripting, Microsoft.Scripting.Core, Microsoft.Dynamic and StdLib intact. No pip packages or new Python installation is needed in the game. These dependencies are not redistributed here.

The bridge reuses Unity.Console's live engine on the Unity main thread. If an old Socket plugin receives an unknown command, requests may time out even while ping works. HTTP 200 or tools/list alone does not prove game control succeeded; inspect returned tool content and game logs.

## Use the scene and animation tools

- `add_character(path, sex)`: load an existing game-host character card, `sex=male/female`.
- `tree`: discover current scene object IDs; IDs can change after scene load.
- `update_transform(objectId, position, rotation, scale)`: update supplied transform fields, rotation in degrees.
- `update_visibility` and `delete`: hide or remove scene objects. Delete does not delete the original card file.
- Camera and screenshot tools operate on the game view. Character animation and MMDD playback are separate controls.

For built-in animations, use `character_animation_list` to find real installed names and `group/category/no`. It supports `search`, `group`, `category`, `offset`, `limit` (1–100), and `refresh=true` after installation/mapping changes. Missing names return nulls and explicit warnings, not a failed entire catalog. `metadata.complete` and `namesComplete` describe skipped slots and name warnings separately; `total/nextOffset` describe matching rows. Every entry's provenance is `unknown`: this is the installed catalog, not a guaranteed base-game list.

Read the target with `character_animation_get(characterId)`. Pause MMDD if initialized, then acquire `character_animation_control(characterId, mode="builtin")` before `character_animation_set(characterId, group, category, no, speed=1)`. Acquisition snapshots animation/time/speed, IK/FK and matching MMDD motion-controller enable flags, then disables that character's MMDD bone control and IK/FK. It retains tracks and camera keys. Walking may be in place; no scene translation is applied.

Always use `character_animation_control(characterId, mode="restore")` in your client's cleanup/finally step, before saving/reloading scenes or closing Studio. Snapshots are memory-only; failed restoration retains them for retry. Morph tracks, other constraints and physical simulation history are not restored by this tool. Set/restore wait for asynchronous animation loading and verify evaluated Animator time within 0.05 of the requested time; they time out after three seconds rather than claiming a reset based on an old loop counter.

MMDD tools: `mmdd_status`, `mmdd_pause`, `mmdd_seek`, `mmdd_play`, `mmdd_load_camera`, `mmdd_record_camera`, `mmdd_export_camera`. Camera paths are on the game host. Recording replaces the key at that frame; export requires a new filename. Pause before manually adjusting and recording a camera.

### Export and search a persistent animation catalog

Run these **Python 3 client utilities** from the extracted package or source root (standard library only):

```sh
python scripts/animation_catalog.py export --cache animation-catalog.json --url http://127.0.0.1:8766/
python scripts/animation_catalog.py find --cache animation-catalog.json --search 歩
python scripts/animation_catalog.py validate --cache animation-catalog.json --url http://127.0.0.1:8766/
```

Export refuses to overwrite files. It writes JSON, UTF-8 CSV and `.metadata.json`; keep CSV and its metadata together. It checks pagination/count/hash consistency. Metadata includes UTC time, runtime session and versions, warnings, content hash, and an installation path/size/mtime inventory fingerprint. This fingerprint is not a hash of every asset. Offline find does not contact the game. Validate refreshes and exits 2 when the snapshot is stale; re-export after game/MOD/mapping changes or a restart. Runtime slot numbers are not portable across installations.

## Build the complete pair from source

Requirements: Windows, .NET SDK 8 or later (tested with 9.0.306), and your legally installed game/dependency DLLs in their normal locations. No game DLLs are committed. The local plugin project targets .NET Framework 3.5 against installed assemblies; NuGet supplies build-time framework references. Internet access to NuGet is required on first restore.

```powershell
.\Rebuild-MMDD.ps1 -GameDir 'C:\Games\Koikatu' -OutputDir '.\dist'
```

The output is a matched EXE/plugin pair with installer, docs, licenses, sources and a hash manifest. The vendored plugin source is pinned in `SOURCE-PROVENANCE.md`; a clone of this repository is sufficient without fetching submodules. Python checks:

```sh
python -m unittest discover -s extensions/KKStudioSocket/tests -v
python -m unittest discover -s tests -v
```

## Validation status

1.2.1 builds on Windows; 25 Python contract tests and installed IronPython/CLR mock execution passed. HTTP tool registration and game get calls were checked. Real standing → walking → standing was observed on 1.2.0 and original animation/speed/IK/FK restored; it was an in-place walk. **1.2.1 full catalog export, real asynchronous-time reset and actual MMDD bone-controller handoff remain pending a saved-scene Studio restart and acceptance test.** The release is marked prerelease for this reason; stubs and tool registration are not visual acceptance.
