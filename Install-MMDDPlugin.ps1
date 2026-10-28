param([Parameter(Mandatory=$true)][string]$GameDir)
$ErrorActionPreference = 'Stop'
$gameExe = [IO.Path]::GetFullPath((Join-Path $GameDir 'CharaStudio.exe'))
if (-not (Test-Path $gameExe)) { throw 'CharaStudio.exe not found in GameDir' }
$running = Get-CimInstance Win32_Process -Filter "Name='CharaStudio.exe'" | Where-Object { $_.ExecutablePath -eq $gameExe }
if ($running) { throw 'Save your scene and close this CharaStudio before replacing its plugin.' }
$target = Join-Path $GameDir 'BepInEx\plugins\KK_KKStudioSocket.dll'
$source = Join-Path $PSScriptRoot 'game-plugin\KK_KKStudioSocket.dll'
if (-not (Test-Path $source)) { throw 'Built MMDD-enabled plugin is missing' }
if (Test-Path $target) {
 $backup = Join-Path $PSScriptRoot ('plugin-backup-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
 New-Item -ItemType Directory $backup | Out-Null
 Copy-Item $target $backup
}
Copy-Item $source $target -Force
if ((Get-FileHash $source).Hash -ne (Get-FileHash $target).Hash) { throw 'Installed plugin hash mismatch' }
Write-Output 'Plugin installed. Start CharaStudio, open VNGE > Utilities > MMD Director, then restart the MCP client/server.'
