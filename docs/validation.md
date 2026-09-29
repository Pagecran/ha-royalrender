# Validation / release status

This is an initial implementation, not yet a certified production deployment.
Target: HA Core 2026.9.4 on HAOS, Windows Server 2025 24H2, RR 9.1.x.

## Experimental Linux preview 0.2.0b1

Linux installer and service smoke test passed on GitHub Actions Ubuntu
(run `36584999304`): root installation with a dedicated unprivileged account,
systemd unit validation, configuration permissions 0640, refusal to overwrite an
existing installation, service start, authenticated HTTP snapshot, restart and stop.
The test uses a deliberately fake SDK and never contacts an RR server.
Linux bridge tests, HA runtime tests and HACS validation also passed in that run.
Local Windows tests: 19 passed, one Linux-only test skipped.

Inspection of the vendor distribution confirmed that Linux native modules reside
in `bin/lx64/lib`; adapter search paths and service `LD_LIBRARY_PATH` now account
for this. Native RR Linux loading, ABI compatibility and real farm commands
remain untested. See [Linux installation and validation boundaries](linux.md).

The RR 9.1.28 installation was inspected in read-only mode. Native SDK symbols
and signatures were confirmed for client status, groups, job info, cEnable,
cDisable, cAbortAfterFrameDisable, cUseWorking, cIgnoreWorking and
jobSend_ChangeClientAssignment. The binding reports version 9.1.27 in this RR
installation. Native group membership uses global client indices, not sorted
list positions. Boolean fields and callable methods are handled separately.

## Automated verification

Post-v0.1.1 hotfix `9679c6a`: 16 local tests passed. The SDK exposes
`sceneDisplayName` as a method; returning the method rather than calling it
caused HTTP 500 when serializing snapshots. The regression test now serializes
a complete adapter snapshot, and a live read-only snapshot also passed JSON
serialization with strict finite-number handling.

0.1.1: 15 local bridge/filter tests passed, including the 10-day submission
boundary, active-only mode, retention of old blocked/pending/rendering jobs,
omission of old finished/manually disabled jobs, ordering and immutable input.

Local results on 29 September 2026: 14 bridge tests passed, Python compilation
passed and both PowerShell installer scripts passed syntax parsing. Read-only
live SDK snapshot returned 545 jobs, 47 machines and 13 groups with exact string
job IDs. No live control command was tested. HA integration tests are provided
for Linux CI against Core 2026.9.4 (Python 3.14), separate from the bridge's
Python 3.13 vendor SDK environment.

GitHub Actions also passed the 14 bridge tests on both Windows and Linux and
the 3 integration tests with Home Assistant Core 2026.9.4 / Python 3.14:
UI setup/duplicate detection, entity setup/discovery/unavailability/unload, and
group-assignment service payloads. These are mocked HA runtime tests, not an
installation on the studio's HAOS instance.
HACS repository validation passed (brand-catalog registration excluded, as this
is a custom repository). Workflow run: 36569511054, attempt 2.

Run `python -m pytest -q`. Tests use an injected SDK and local ephemeral HTTP server:
- historical errors / new incidents / recovery / reset / expiration / deletion;
- correct global client index and 64-bit job IDs;
- add/remove/replace group semantics, missing groups/machines/jobs;
- authentication, malformed/unsupported commands, no implicit retry;
- failed or stale RR polling and read-only operation.

## Optional live read-only check

From the bridge Python environment, with your own Config instance:

```python
from rr_ha_bridge.sdk import RoyalRenderSDK
from rr_ha_bridge.config import Config
config = Config.load(r"C:\ProgramData\RoyalRenderHABridge\config.json")
snapshot = RoyalRenderSDK(config).snapshot()
print(len(snapshot["jobs"]), len(snapshot["machines"]), len(snapshot["groups"]))
```

This only requests status. Do not commit its output: it can contain private job,
user and machine names. No production commands have been sent during development.

## Pilot deployment — 29 September 2026

User-confirmed on Windows Server 2025 / HAOS Core 2026.9.4:

- Python 3.13 x64 installed; bridge installed in a dedicated virtual environment.
- Original pywin32 executable failed to start (missing DLL, then service-manager
  module lookup failure). An explicit Python service host resolved startup.
- Windows service reported Running under LocalSystem and loaded the RR SDK.
- After hotfix `9679c6a`, the authenticated local API returned farm counters.
- Home Assistant connected successfully; the user confirmed clients are displayed.
- Unavailable buttons were explained by the default `allow_commands=false`.
  Instructions for enabling commands were supplied; execution and live command
  behavior have not been confirmed.
- A dashboard is being prepared by the user and will be supplied later.

Reproduction and recovery steps: [French installation guide](installation-fr.md).
No actual credentials, internal addresses or private configuration are included.
The service-host workaround is documented; it is not yet built into the v0.1.1 installer.

## Still to validate on the target installation

- HA reconfigure/reauth, discovery of newly added clients and the finished dashboard.
- Windows service behavior after a server reboot and recovery after process failure.
- One expressly designated test machine and disposable job: commands, existing
  Working Hours policy, after-frame behavior and group changes during execution.
- TLS/firewall and simulated service/network outages with Home Assistant.

Automated tests do not install services, alter firewalls or send RR commands.
The pilot deployment was performed by the user using the provided instructions.
