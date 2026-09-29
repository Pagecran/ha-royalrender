#Requires -RunAsAdministrator
[CmdletBinding()]
param([string]$InstallDir = "$env:ProgramData\RoyalRenderHABridge")
$ErrorActionPreference = 'Stop'
Stop-Service RoyalRenderHABridge -ErrorAction SilentlyContinue
& "$InstallDir\venv\Scripts\python.exe" -m rr_ha_bridge.windows_service remove
if ($LASTEXITCODE -ne 0) { throw 'Service removal failed.' }
Write-Host "Service removed. Configuration, logs and venv preserved in $InstallDir."
