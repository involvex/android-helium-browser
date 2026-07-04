<#
.SYNOPSIS
  Pushes the unpacked Involvex AI Agent extension to a connected Android device.

.DESCRIPTION
  Removes the old copy on the device, pushes the current extension source, and
  verifies the manifest version that landed. Intended for the "Load unpacked"
  workflow in the Involvex/Helium browser.

.PARAMETER DeviceDir
  Target directory on the device. Default: /sdcard/repos/ai-agent

.PARAMETER Serial
  Optional adb device serial (use when more than one device is attached).

.EXAMPLE
  pwsh scripts/adb-update.ps1
  pwsh scripts/adb-update.ps1 -Serial emulator-5554
#>
[CmdletBinding()]
param(
  [string]$DeviceDir = "/sdcard/repos/ai-agent",
  [string]$Serial
)

$ErrorActionPreference = "Stop"

# Resolve the extension folder relative to this script (repo-root/involvex/ai-agent).
$repoRoot = Split-Path -Parent $PSScriptRoot
$extDir = Join-Path $repoRoot "involvex\ai-agent"
$manifestPath = Join-Path $extDir "manifest.json"

if (-not (Get-Command adb -ErrorAction SilentlyContinue)) {
  throw "adb not found on PATH. Install platform-tools or add it to PATH."
}
if (-not (Test-Path $manifestPath)) {
  throw "manifest.json not found at $manifestPath"
}

# Build adb args with an optional serial so multi-device setups work.
$adbBase = @()
if ($Serial) { $adbBase += @("-s", $Serial) }

# Runs adb with the given argument array. Flags like "-rf" are passed through
# safely because they live inside the array, not as PowerShell parameters.
function Invoke-Adb {
  param([string[]]$AdbArgs)
  & adb @adbBase @AdbArgs
  if ($LASTEXITCODE -ne 0) { throw "adb $($AdbArgs -join ' ') failed (exit $LASTEXITCODE)." }
}

# Confirm exactly one usable device (unless a serial was given).
$devices = (& adb devices) -split "`r?`n" |
  Where-Object { $_ -match "\tdevice$" } |
  ForEach-Object { ($_ -split "\t")[0] }
if ($devices.Count -eq 0) {
  throw "No authorized device found. Connect a device and enable USB debugging."
}
if (-not $Serial -and $devices.Count -gt 1) {
  throw "Multiple devices attached ($($devices -join ', ')). Re-run with -Serial <serial>."
}

$localVersion = (Get-Content $manifestPath -Raw | ConvertFrom-Json).version
Write-Host "Extension : $extDir" -ForegroundColor Cyan
Write-Host "Local ver : $localVersion" -ForegroundColor Cyan
Write-Host "Device dir: $DeviceDir" -ForegroundColor Cyan

Write-Host "`nCurrent contents on device:" -ForegroundColor DarkGray
& adb @adbBase shell "ls -la $DeviceDir 2>/dev/null || echo '  (not present yet)'"

Write-Host "`nRemoving old copy..." -ForegroundColor Yellow
Invoke-Adb @("shell", "rm -rf '$DeviceDir'")
Invoke-Adb @("shell", "mkdir -p '$DeviceDir'")

Write-Host "Pushing new build..." -ForegroundColor Yellow
# Push folder contents (the trailing \. keeps files at the target root, not nested).
Invoke-Adb @("push", "$extDir\.", $DeviceDir)

# Verify the manifest version that actually landed on the device.
Write-Host "`nVerifying manifest on device..." -ForegroundColor Yellow
$deviceManifest = & adb @adbBase shell "cat $DeviceDir/manifest.json" 2>$null
$deviceVersion = $null
if ($deviceManifest) {
  try { $deviceVersion = ($deviceManifest | ConvertFrom-Json).version } catch {}
}
if ($deviceVersion -eq $localVersion) {
  Write-Host "OK: device manifest reports v$deviceVersion" -ForegroundColor Green
} else {
  Write-Warning "Device manifest version '$deviceVersion' != local '$localVersion'. Check the push."
}

if ($deviceManifest -match "side_panel") {
  Write-Warning "Device manifest still contains 'side_panel' - stale copy? Remove + reload the extension."
}

Write-Host "`nDone." -ForegroundColor Green
Write-Host "Next: chrome://extensions -> Remove the old one -> Load unpacked -> $DeviceDir" -ForegroundColor Cyan

$running = & adb @adbBase shell "pgrep -l helium 2>/dev/null || pgrep -l involvex 2>/dev/null"
if ($running) {
  Write-Host "`nBrowser process:" -ForegroundColor DarkGray
  Write-Host $running
} else {
  Write-Host "`nBrowser does not appear to be running." -ForegroundColor DarkGray
}
