# Runtime dependencies and paired upgrades

The HTTP server and game plugin are separate components. Install the matching pair; the current game plugin is 1.2.1.0. See [README](README.md) for setup, supported versions, all 34 tools and acceptance limits.

A successful tools/list proves the HTTP server registered tools, not that the game loaded the plugin. Upstream Socket 1.0.0 has no MMDD handler; custom 1.1.0 has MMDD but no character animation handler. Save the scene, close Studio, run the paired installer, restart Studio and check the actual loaded version in BepInEx/LogOutput.log.

The original scene tools use BepInEx/KKAPI/websocket-sharp/Newtonsoft.Json. The fixed animation bridge additionally uses the installed VNGE 42.9 Unity.Console engine and its existing IronPython/Microsoft.Scripting/StdLib libraries. MMDD tools require MMD Director 2.9.4 initialized. These are installed-environment dependencies, not included in the paired ZIP. Do not overwrite the entire BepInEx directory to resolve a timeout.

If the correct plugin is loaded but a request times out, inspect the game exception and main-thread responsiveness. Increasing the timeout cannot supply a missing handler. Tool returned content must indicate success; HTTP 200 alone is insufficient.
