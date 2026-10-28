# Source provenance and paired versions

- MCP server: fork of https://github.com/great-majority/KoikatuMCP at d17c27006f8d9f7f45861e0fe77ee3db5518adab. MIT, see LICENSE. Upstream history is retained.
- Game plugin: fork of https://github.com/great-majority/KKStudioSocket at ee47ca555ff2764d69ea41a46e8fb4dbaf436e25. GPL-3.0, see extensions/KKStudioSocket/LICENSE.
- Paired game plugin source: https://github.com/RicterZ/KKStudioSocket/tree/3c81bc8ad103570284accd2a63d6a7778848a823, version 1.2.1.0. The tracked vendored files match that commit, including build configuration and tests.
- Local implementation provenance: tested Windows source delivery b804480, extending the original HTTP transport, MMDD and character animation controls. This fork restores upstream Git ancestry; local deployment-only root commits are not used as its base.
- No game binaries, character cards, MODs, VNGE distribution scripts, credentials, private configuration or local caches are included.
- The paired distribution contains two separate programs communicating via WebSocket; the server is MIT and the game plugin is GPL-3.0. The plugin's corresponding source and license ship with its binary. Source links and preserved notices are not a license for game dependencies.
