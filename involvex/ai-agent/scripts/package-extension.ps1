# Packages the Involvex AI Agent extension into a store-ready zip.
# Excludes local secrets (.env) and build output.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$manifest = Get-Content manifest.json -Raw | ConvertFrom-Json
$version = $manifest.version
$dist = Join-Path $root 'dist'
New-Item -ItemType Directory -Force -Path $dist | Out-Null
$out = Join-Path $dist "involvex-ai-agent-$version.zip"
if (Test-Path $out) { Remove-Item $out }

$items = @('manifest.json', 'src', 'icons', 'README.md', 'CHANGELOG.md') |
  Where-Object { Test-Path $_ }
Compress-Archive -Path $items -DestinationPath $out -Force

Write-Host "Built $out"
