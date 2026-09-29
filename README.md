# Royal Render for Home Assistant

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="custom_components/royalrender/brand/dark_logo.png">
  <img src="custom_components/royalrender/brand/logo.png" alt="Royal Render" width="221">
</picture>

[![HACS: Custom](https://img.shields.io/badge/HACS-Custom-41BDF5?logo=homeassistant&logoColor=white)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Pagecran&repository=ha-royalrender&category=integration)
[![Release](https://img.shields.io/github/v/release/Pagecran/ha-royalrender?include_prereleases)](https://github.com/Pagecran/ha-royalrender/releases)
[![Tests](https://github.com/Pagecran/ha-royalrender/actions/workflows/tests.yml/badge.svg)](https://github.com/Pagecran/ha-royalrender/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Custom Home Assistant integration (HACS) and a separate Windows/Linux bridge using the
official Royal Render Python SDK. Public, generic project: no studio addresses,
credentials, proprietary SDK binaries or production scenes are distributed.

**[Quick start](#quick-start)** · **[Windows bridge](#windows-installation)** ·
**[HACS setup](#hacs-installation)** · **[Renderfarm dashboard](docs/dashboard.md)** ·
**[Installation & troubleshooting (FR)](docs/installation-fr.md)** ·
**[Linux (experimental)](docs/linux.md)** ·
**[Releases](https://github.com/Pagecran/ha-royalrender/releases)** ·
**[Report an issue](https://github.com/Pagecran/ha-royalrender/issues/new)**

**0.2.0b1 — Linux experimental preview; stable release: v0.1.2.** Target: Home Assistant Core 2026.9.4
on HAOS, Royal Render 9.1.x, Windows Server 2025. A pilot installation now runs
as a Windows service and displays clients in Home Assistant, with the bridge
fix and service-host workaround documented in the [installation guide](docs/installation-fr.md).
Live write commands are still unverified. See
[validation](docs/validation.md) for what has actually been tested.

## Quick start

### 1. Install the Windows bridge

For a Linux server with native Royal Render, use the separate
[experimental Linux/systemd installation guide](docs/linux.md).

[Download v0.1.1 (ZIP)](https://github.com/Pagecran/ha-royalrender/archive/refs/tags/v0.1.1.zip),
extract it on the Royal Render server and follow the [Windows installation](#windows-installation).
The v0.1.1 archive predates the JSON fix: apply the
[bridge hotfix and Windows service workaround](docs/installation-fr.md) before connecting HA.
Keep the bridge URL and generated API key for the Home Assistant setup.

### 2. Open this repository in HACS

[![Open your Home Assistant instance and open this repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Pagecran&repository=ha-royalrender&category=integration)

HACS must already be installed ([HACS installation guide](https://www.hacs.xyz/docs/use/download/download/)).
The button opens the repository in your own Home Assistant instance; download
**Royal Render**, select the pre-release if needed, then restart Home Assistant.
If asked by My Home Assistant, enter your Home Assistant URL.

### 3. Add and configure the integration

[![Open your Home Assistant instance and start setting up Royal Render.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=royalrender)

Use this second button **after installation and restart**. Enter the bridge URL
and API key. The Windows service is installed separately; HACS installs only the
Home Assistant integration. A [manual HACS fallback](#hacs-installation) is available below.

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
   v0.1.2 is a standard release. Enable beta versions only to select the Linux
   preview v0.2.0b1; existing Windows/HA users do not need the preview for branding.
2. Download Royal Render and restart Home Assistant.
3. Settings → Devices & services → Add integration → **Royal Render**.
4. Enter `http://your-bridge:8787` (or HTTPS) and the generated API key.

Use **Reconfigure** to change URL/key and **Options** for the update interval.
Options also sets the submission history window (default **10 days**, **0** for
active jobs only). Active jobs (rendering, pending, or disabled because of errors)
stay visible regardless of age. Recent finished/manually disabled jobs are included
within the window, newest submissions first. This only filters the HA display;
it does not delete or modify RR jobs. Upgrade the bridge as well to provide submission
timestamps. The bridge should use the same local timezone as the RR server.
When RR is inaccessible the integration cannot complete its initial setup.
Controls remain unavailable if the bridge was installed without `-EnableCommands`.
For an existing installation, see [enabling commands](docs/installation-fr.md#activer-les-boutons).

### Dashboard

Royal Render light/dark logos are bundled with the integration for Home Assistant.
See [branding and dashboard instructions](docs/branding.md) to use the logo in a
Picture card; a ready-to-copy example is in `examples/logo-card.yaml`.

The user-contributed [Renderfarm dashboard](examples/renderfarm-dashboard.yaml)
provides job tables, a machine card and a control popup using Bubble Card and
card-mod. See [import instructions and adaptation notes](docs/dashboard.md).
It uses placeholder entities and is a starting point, not a fully validated UI.
`examples/dashboard.yaml` remains the minimal incident-monitoring example.

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
Brand artwork belongs to its respective owners; see [asset attribution](docs/branding.md#sources-and-attribution).
