# KKStudioSocket — paired KoikatuMCP extension

This is the game-side fork of [great-majority/KKStudioSocket](https://github.com/great-majority/KKStudioSocket), licensed under GPL-3.0 (see LICENSE).

It runs **inside KK CharaStudio as a BepInEx plugin**. It is not the MCP HTTP server. Use it together with [RicterZ/KoikatuMCP](https://github.com/RicterZ/KoikatuMCP), which provides the independent Windows EXE and the paired download/build instructions.

The 1.2.1 extension adds VNGE/MMDD controls, built-in character animation list/get/set/control, incomplete-catalog warnings/cache metadata, and asynchronous Animator time verification. It retains the original scene/camera tools. Default game endpoint: `ws://127.0.0.1:8765/ws`.

Save the scene and close Studio before installing the DLL. Confirm `Loading [KKStudioSocket 1.2.1]` in the game log on restart. The paired package's installer backs up the old DLL and copies only this plugin. Game assets and dependencies are not included. Required existing libraries: BepInEx, KKAPI, websocket-sharp and Newtonsoft.Json. Animation bridge requires initialized VNGE 42.9 and its Unity.Console/IronPython runtime; MMDD commands require MMD Director 2.9.4 opened. KKS is not validated.

Build against the installed game and Console libraries:

```powershell
dotnet build KKStudioSocket.Local.csproj -c Release '-p:GameDir=C:\Games\Koikatu' --configfile nuget.local.config -o .\dist
```

Use .NET SDK 8+ on Windows (tested SDK 9.0.306). The target is .NET Framework 3.5. No proprietary game assemblies are redistributed. See `KKStudioSocket.Local.csproj` for the installed-library reference locations.

Contract tests (Python 3, standard library):

```sh
python -m unittest discover -s tests -v
```

The fixed bridges run on the Unity main thread using the existing Unity.Console engine, with request JSON passed as a variable. They do not offer an arbitrary-code MCP tool. Read all animation-control/restore limitations in the paired server README before using the scene.

Validation: Windows build, contract tests and installed IronPython mock checks passed. Actual 1.2.1 full catalog, time reset and MMDD handoff remain pending runtime acceptance; use the paired prerelease and do not confuse mock tests with game validation.
