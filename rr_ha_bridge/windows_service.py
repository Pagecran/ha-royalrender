"""Windows SCM service wrapper. Installed explicitly by install.ps1."""
import os
from pathlib import Path
import subprocess
import winreg

import servicemanager
import win32event
import win32service
import win32serviceutil


class RoyalRenderBridgeService(win32serviceutil.ServiceFramework):
    _svc_name_ = "RoyalRenderHABridge"
    _svc_display_name_ = "Royal Render Home Assistant Bridge"
    _svc_description_ = "Royal Render monitoring and explicit commands for Home Assistant."

    def __init__(self, args):
        super().__init__(args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)

    def SvcDoRun(self):
        registry = rf"SYSTEM\CurrentControlSet\Services\{self._svc_name_}\Parameters"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, registry) as key:
            python = winreg.QueryValueEx(key, "PythonExe")[0]
            config = winreg.QueryValueEx(key, "ConfigPath")[0]
        log = str(Path(config).parent / "bridge.log")
        process = subprocess.Popen(
            [python, "-m", "rr_ha_bridge.server", "--config", config, "--log-file", log],
            cwd=str(Path(config).parent), stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        servicemanager.LogInfoMsg("Royal Render bridge started")
        try:
            while win32event.WaitForSingleObject(self.stop_event, 1000) == win32event.WAIT_TIMEOUT:
                if process.poll() is not None:
                    servicemanager.LogErrorMsg(f"Royal Render bridge exited with code {process.returncode}")
                    # Nonzero termination lets SCM recovery restart the service.
                    os._exit(1)
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill()
            servicemanager.LogInfoMsg("Royal Render bridge stopped")


if __name__ == "__main__":
    win32serviceutil.HandleCommandLine(RoyalRenderBridgeService)
