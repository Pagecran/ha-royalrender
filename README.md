# Royal Render for Home Assistant

Custom Home Assistant integration (HACS) and a separate Windows bridge using the
official Royal Render Python SDK. Public, generic project: no studio addresses,
credentials, proprietary SDK binaries or production scenes are distributed.

**Initial release 0.1.0 — validation build.** Target: Home Assistant Core 2026.9.4
on HAOS, Royal Render 9.1.x, Windows Server 2025. Installation on HAOS and Windows
SCM and live write commands still require an agreed test deployment. See
[validation](docs/validation.md) for what has actually been tested.

## Features

- Per-machine native RR status, rendering activity, job IDs and CPU usage.
- Farm counters, queue attributes, group membership and problem-job list.
- A problem binary sensor for dashboards/notifications. Example dashboard with
  red/orange per-job icons in `examples/dashboard.yaml`.
- Explicit machine buttons: Enable, Disable, Disable after frame, Use Working
  Hours, Ignore Working Hours. Working Hours uses the existing RR schedule;
  this integration does not edit it. Disable is the native RR cDisable command
  and can interrupt work. Use the after-frame action when that is intended.
- Home Assistant `royalrender.assign_groups` action: add/remove/replace client
  assignments using the groups' current members. **Not a dynamic group link.**
- Bridge failures/stale data make HA entities unavailable. Machine status stays
  separate from rendering activity: idle, working hours, disabled and offline
  are not conflated.

## Architecture

```text
Home Assistant custom integration <-- authenticated HTTP(S) --> Windows bridge
                                                            <-- SDK --> rrServer
```

SDK calls run on one dedicated thread; HA polls a cache (15 seconds by default).
The bridge remains separate from the RR service. Commands are never retried
automatically. API v1 uses full RR job IDs as **strings**, preserving 64-bit precision.
Jobs are queue attributes rather than thousands of permanent HA entity records.

## Windows installation

1. Install a **64-bit Python version supported by your RR SDK**. RR 9.1.28 with
   Python 3.13 was used for development; the bridge supports Python >=3.11 but a
   matching vendor `.pyd` is mandatory. Home Assistant's Python is independent.
2. Download/clone this repository to the server; use a tagged version for deployment.
3. In an elevated PowerShell, run (replace all example values):

```powershell
.\scripts\install.ps1 `
  -PythonExe 'C:\Python313\python.exe' `
  -RrRoot 'C:\RoyalRender' `
  -RrHost 'rr-server.example.local' `
  -ListenHost '0.0.0.0' -ListenPort 8787
```

Add `-EnableCommands` for the control buttons/actions. An optional
`-RrCredential (Get-Credential)` supplies RR credentials. `-RrPort`, `-InstallDir`,
`-TlsCert` and `-TlsKey` are configurable. Without TLS, HTTP is for a trusted LAN;
for other networks use TLS (certificate trusted by HA) or a TLS reverse proxy.

The installer creates a venv, an API key and persistent bridge UUID, stores them
in an ACL-restricted `config.json` under ProgramData, and registers a Windows
service. It **does not start the service or change firewall rules**. All addresses
are installation parameters. The key is read from the config, not printed in logs.

4. Set the service Log On account if RR/SDK is on a network share. LocalSystem
   must have access, or use a service account with the required permissions.
   Use local or UNC paths; mapped drives are not dependable in services.
5. Permit the selected TCP port from Home Assistant in Windows/network firewalls.
6. Start explicitly: `Start-Service RoyalRenderHABridge`.

Logs rotate under ProgramData (3 backups, 5 MB each). The service is automatic-start
and configured for recovery. SDK/network failures are retried through polling;
pending commands are not replayed.

### Reconfigure / upgrade / uninstall

Stop the service, back up `config.json`, edit addresses/port/credentials and restart.
Keep `bridge_id` to retain entity identities. To upgrade, stop the service and run
the installed venv's Python `-m pip install --upgrade 'C:\path\to\new-source[windows]'`,
then restart. Never overwrite the configuration with an example file.
Use `scripts/uninstall.ps1` to remove the service while retaining config/logs.

## HACS installation

1. HACS → Custom repositories → add `https://github.com/Pagecran/ha-royalrender`,
   category **Integration**. This is a custom repository, not a HACS catalog listing.
   The initial release is marked pre-release: enable beta versions in HACS if
   needed to select it.
2. Download Royal Render and restart Home Assistant.
3. Settings → Devices & services → Add integration → **Royal Render**.
4. Enter `http://your-bridge:8787` (or HTTPS) and the generated API key.

Use **Reconfigure** to change URL/key and **Options** for the update interval.
When RR is inaccessible the integration cannot complete its initial setup.
Controls remain unavailable if the bridge was installed without `-EnableCommands`.

## Job health rules

- 🔴 `blocked`: RR explicitly marks the job disabled because of errors.
- 🟠 `warning`: error count increased since a previous poll, in the last 5 minutes.
- New frame completion without additional errors clears the warning (recovery).
- Finished jobs and manually disabled jobs have distinct states.
- Existing lifetime errors on first observation are a baseline, not new incidents.
  They remain visible in `errors`. No fictitious "recent" timestamp is invented.
- No-progress alone is not classified as an error: a legitimate frame may be long.

This initial version reports counts/status, not parsed render-log excerpts or a
complete retained error history. Bridge restart resets the recent-error baseline.
An unavailable bridge is not reported as "zero problems".

## Actions

Use Developer tools → Actions; the integration selection is a config-entry selector.
Example group assignment (IDs/names below are illustrative):

```yaml
action: royalrender.assign_groups
data:
  config_entry_id: YOUR_INTEGRATION_ENTRY_ID
  job_id: "1877000000000000001"
  groups: [CPU]
  mode: add
```

The Queue sensor attributes provide the actual job IDs and group names. `replace`
deassigns all other machines; `remove` removes the selected members. Empty/unknown
groups are rejected. RR authorization remains authoritative. An accepted response
means RR accepted the request, not that a running frame has already stopped.

High-frequency queue attributes can grow Recorder history. Consider excluding
the Queue and Problem jobs sensors from Recorder while retaining counters and
the problem binary sensor for history/automations.

## Development

```text
python -m venv .venv
.venv/Scripts/python -m pip install -e .[test]
.venv/Scripts/python -m pytest
```

The SDK adapter is injectable: automated tests never connect to or modify a farm.
An optional **read-only** live check is documented in `docs/validation.md`.
All code is MIT licensed; Royal Render itself and its SDK remain proprietary.
