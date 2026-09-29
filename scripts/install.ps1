#Requires -RunAsAdministrator
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$PythonExe,
    [Parameter(Mandatory)][string]$RrRoot,
    [Parameter(Mandatory)][string]$RrHost,
    [int]$RrPort = 7773,
    [string]$ListenHost = '0.0.0.0',
    [int]$ListenPort = 8787,
    [string]$InstallDir = "$env:ProgramData\RoyalRenderHABridge",
    [PSCredential]$RrCredential,
    [switch]$EnableCommands,
    [string]$TlsCert = '',
    [string]$TlsKey = ''
)
$ErrorActionPreference = 'Stop'
function Run-Python([string]$Exe, [string[]]$Arguments) {
    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Python command failed (exit $LASTEXITCODE)" }
}
if (Get-Service RoyalRenderHABridge -ErrorAction SilentlyContinue) {
    throw 'Service already exists. See README upgrade/reconfiguration procedure.'
}
if (Test-Path $InstallDir) { throw 'Choose a new installation directory; existing configuration is preserved.' }
if (-not (Test-Path "$RrRoot\SDK\External\Python\rr_python_utils")) { throw 'Royal Render SDK not found.' }
$Source = Split-Path $PSScriptRoot -Parent
New-Item -ItemType Directory -Path $InstallDir | Out-Null
# Configuration contains API/RR credentials. Restrict this directory to SYSTEM and administrators.
& icacls.exe $InstallDir /inheritance:r /grant:r '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Could not restrict installation directory permissions.' }
Run-Python $PythonExe @('-m', 'venv', "$InstallDir\venv")
$Python = "$InstallDir\venv\Scripts\python.exe"
Run-Python $Python @('-m', 'pip', 'install', "${Source}[windows]")
$ApiKey = & $Python -c 'import secrets; print(secrets.token_urlsafe(48))'
if ($LASTEXITCODE -ne 0) { throw 'Could not generate API key.' }
$Config = @{
    bridge_id = [guid]::NewGuid().ToString()
    api_key = $ApiKey.Trim()
    rr_root = $RrRoot
    rr_host = $RrHost
    rr_port = $RrPort
    listen_host = $ListenHost
    listen_port = $ListenPort
    poll_seconds = 15
    error_window_seconds = 300
    allow_commands = [bool]$EnableCommands
    rr_user = ''
    rr_password = ''
    tls_cert = $TlsCert
    tls_key = $TlsKey
}
if ($RrCredential) {
    $Config.rr_user = $RrCredential.UserName
    $Config.rr_password = $RrCredential.GetNetworkCredential().Password
}
$ConfigPath = "$InstallDir\config.json"
$Config | ConvertTo-Json | Set-Content -LiteralPath $ConfigPath -Encoding UTF8
Run-Python $Python @('-c', 'from rr_ha_bridge.config import Config; import sys; Config.load(sys.argv[1])', $ConfigPath)
Run-Python $Python @('-m', 'rr_ha_bridge.windows_service', '--startup', 'auto', 'install')
$Registry = 'HKLM:\SYSTEM\CurrentControlSet\Services\RoyalRenderHABridge\Parameters'
New-Item -Path $Registry -Force | Out-Null
New-ItemProperty -Path $Registry -Name PythonExe -Value $Python -PropertyType String -Force | Out-Null
New-ItemProperty -Path $Registry -Name ConfigPath -Value $ConfigPath -PropertyType String -Force | Out-Null
& sc.exe failure RoyalRenderHABridge reset= 86400 actions= restart/10000/restart/30000/restart/60000 | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Could not configure service recovery.' }
Write-Host "Service installed, NOT started. Configuration and API key: $ConfigPath"
Write-Host 'Check service account access to RR, network/firewall and TLS, then Start-Service RoyalRenderHABridge.'
