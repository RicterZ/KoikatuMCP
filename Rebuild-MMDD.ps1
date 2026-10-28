param(
 [Parameter(Mandatory=$true)][string]$GameDir,
 [string]$OutputDir=(Join-Path $PSScriptRoot 'dist')
)
$ErrorActionPreference = 'Stop'
$GameDir = [IO.Path]::GetFullPath($GameDir)
$OutputDir = [IO.Path]::GetFullPath($OutputDir)
if (-not (Test-Path (Join-Path $GameDir 'CharaStudio.exe'))) { throw 'GameDir must contain KK CharaStudio.exe' }
$pluginRoot = Join-Path $PSScriptRoot 'extensions\KKStudioSocket'
$project = Join-Path $pluginRoot 'KKStudioSocket.Local.csproj'
$config = Join-Path $pluginRoot 'nuget.local.config'
dotnet build $project -c Release "-p:GameDir=$GameDir" --configfile $config -o (Join-Path $OutputDir 'game-plugin')
if ($LASTEXITCODE -ne 0) { throw 'Game plugin build failed' }
dotnet publish (Join-Path $PSScriptRoot 'src\KoikatuMCP.csproj') -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true -o $OutputDir
if ($LASTEXITCODE -ne 0) { throw 'MCP publish failed' }
foreach ($file in @('README.md','LICENSE','SOURCE-PROVENANCE.md','Install-MMDDPlugin.ps1')) {
 Copy-Item (Join-Path $PSScriptRoot $file) $OutputDir -Force
}
Copy-Item (Join-Path $PSScriptRoot 'scripts') $OutputDir -Recurse -Force
Copy-Item (Join-Path $pluginRoot 'LICENSE') (Join-Path $OutputDir 'LICENSE-KKStudioSocket') -Force
# Keep corresponding GPL plugin sources with the binary, without game references or outputs.
$source = Join-Path $OutputDir 'plugin-source'
if (Test-Path $source) { Remove-Item $source -Recurse -Force }
New-Item -ItemType Directory $source | Out-Null
foreach ($file in @('LICENSE','README.md','SOURCE-PROVENANCE.md','KKStudioSocket.Local.csproj','nuget.local.config','Directory.Build.props','Directory.Build.targets')) {
 if (Test-Path (Join-Path $pluginRoot $file)) { Copy-Item (Join-Path $pluginRoot $file) $source }
}
Copy-Item (Join-Path $pluginRoot 'src') $source -Recurse
Copy-Item (Join-Path $pluginRoot 'tests') $source -Recurse
Get-ChildItem $source -Directory -Recurse | Where-Object {$_.Name -in @('bin','obj','__pycache__')} | Sort-Object {$_.FullName.Length} -Descending | Remove-Item -Recurse -Force
$hashes = Get-ChildItem $OutputDir -File -Recurse | Where-Object {$_.Name -ne 'SHA256SUMS.txt'} | Sort-Object FullName | ForEach-Object {
 ((Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLower()) + '  ' + $_.FullName.Substring($OutputDir.Length+1).Replace('\','/')
}
[IO.File]::WriteAllLines((Join-Path $OutputDir 'SHA256SUMS.txt'), [string[]]$hashes, (New-Object Text.UTF8Encoding($false)))
Write-Output "Paired distribution ready: $OutputDir"
