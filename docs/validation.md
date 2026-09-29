# Validation / release status

This is an initial implementation, not yet a certified production deployment.
Target: HA Core 2026.9.4 on HAOS, Windows Server 2025 24H2, RR 9.1.x.

The RR 9.1.28 installation was inspected in read-only mode. Native SDK symbols
and signatures were confirmed for client status, groups, job info, cEnable,
cDisable, cAbortAfterFrameDisable, cUseWorking, cIgnoreWorking and
jobSend_ChangeClientAssignment. The binding reports version 9.1.27 in this RR
installation. Native group membership uses global client indices, not sorted
list positions. Boolean fields and callable methods are handled separately.

## Automated verification

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

## Still to validate on the target installation

- HACS install, HA UI config/reconfigure/reauth, dynamic entities and dashboards.
- Windows SCM installation/start/stop/reboot and access under the service account.
- One expressly designated test machine and disposable job: commands, existing
  Working Hours policy, after-frame behavior and group changes during execution.
- TLS/firewall and simulated service/network outages with Home Assistant.

No service is installed automatically by tests, no firewall rule is changed,
and HA or RR production configuration is not modified by development.
