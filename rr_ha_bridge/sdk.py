"""RR 9 SDK adapter. All access is serialized on a dedicated thread by server.py."""
import importlib
import os
from pathlib import Path
import sys


class SDKError(RuntimeError):
    pass


# No arbitrary commands or shell execution exposed through the bridge.
CLIENT_COMMANDS = {
    "enable": "cEnable",
    "disable": "cDisable",
    "disable_after_frame": "cAbortAfterFrameDisable",
    "working_hours": "cUseWorking",
    "ignore_working_hours": "cIgnoreWorking",
}


def value(obj, key):
    item = getattr(obj, key)
    return item() if callable(item) else item


class RoyalRenderSDK:
    def __init__(self, config):
        self.config = config
        self.tcp = None
        self.lib = None
        self.dll_directory = None

    def connect(self):
        root = Path(self.config.rr_root)
        os.environ["RR_ROOT"] = str(root)
        binary = root / "bin" / ("win64" if os.name == "nt" else "lx64")
        if os.name == "nt" and self.dll_directory is None:
            self.dll_directory = os.add_dll_directory(str(binary))
        for path in (binary, root / "SDK/External/Python"):
            if str(path) not in sys.path:
                sys.path.insert(0, str(path))
        self.lib = importlib.import_module("rr_python_utils.load_rrlib").rrLib
        tcp = self.lib._rrTCP("")
        if not tcp.setServer(self.config.rr_host, self.config.rr_port):
            raise SDKError(tcp.errorMessage())
        if self.config.rr_user:
            tcp.setLogin(self.config.rr_user, self.config.rr_password)
        if not tcp.connectAndAuthorize():
            raise SDKError(tcp.errorMessage())
        self.tcp = tcp

    def require(self, result):
        if not result:
            raise SDKError(self.tcp.errorMessage())

    def clients(self):
        self.require(self.tcp.clientGetList())
        return [self.tcp.clients.at(i) for i in range(self.tcp.clients.count())]

    def groups(self, clients):
        groups = self.tcp.clientGetGroups()
        if groups is None or groups.count < 0:
            raise SDKError("Cannot read client groups")
        result = []
        for i in range(groups.count):
            group = groups.clientGroup(i)
            result.append({"name": group.getName(), "clients": [
                c.name() for c in clients if group.isMember_byGlobalIndex(c.listIdx)
            ]})
        return result

    def snapshot(self):
        if self.tcp is None:
            self.connect()
        clients = self.clients()
        machines = []
        for c in clients:
            threads = [c.jobThread(i) for i in range(c.status.maxJobThreads)]
            machines.append({
                "id": c.name(), "name": c.name(), "enabled": bool(c.status.enabled),
                "rendering": any(t.isRendering() for t in threads),
                "states": [t.clientStatusAsStringSingle() for t in threads],
                "jobs": sorted({str(t.jobID) for t in threads if t.isRendering()}),
                "cpu_percent": float(c.status.CPU_Usage),
            })
        groups = self.groups(clients)
        self.require(self.tcp.jobList_GetInfo())
        jobs = []
        for i in range(self.tcp.jobs.getMaxJobsFiltered()):
            jid = self.tcp.jobs.getJobMinInfo_filterQueue(i).ID
            j = self.tcp.jobs.getJobInfo(jid)
            status = j.statusAsString()
            jobs.append({
                # Preserve 64-bit job IDs as strings; JavaScript numbers lose precision.
                "id": str(j.ID), "label": j.IDstr().strip("{} "),
                # RR exposes a local datetime; the bridge runs in the RR server's timezone.
                "submitted_at": j.dateSubmitted.timestamp() if j.dateSubmitted else None,
                "name": j.sceneDisplayName or j.sceneName.replace("\\", "/").rsplit("/", 1)[-1],
                "user": j.userName, "project": j.companyProjectName,
                "layer": j.layer, "status": status,
                "done": int(j.framesDone), "total": int(j.framesTotal),
                "errors": int(j.errorCount), "disabled": bool(j.disabled),
                "disabled_errors": bool(j.disabledBecausOfErrors),
                "rendering": bool(value(j, "isRendering")),
                "finished": status.lower().startswith("finished"),
                "assigned_clients": [c.name() for c in clients if j.clientAssigned(c.listIdx)],
                "rendering_clients": [m["name"] for m in machines if str(j.ID) in m["jobs"]],
            })
        return {"machines": machines, "jobs": jobs, "groups": groups}

    def machine_command(self, name, action):
        if action not in CLIENT_COMMANDS:
            raise ValueError("Unknown machine action")
        if self.tcp is None:
            self.connect()
        matches = [c for c in self.clients() if c.name() == name]
        if len(matches) != 1:
            raise ValueError("Machine not found or ambiguous")
        command = getattr(self.lib._ClientCommand, CLIENT_COMMANDS[action])
        self.require(self.tcp.clientSendCommand([matches[0].listIdx], command, ""))
        return {"accepted": True, "machine": name, "action": action}

    def assign_groups(self, job_id, names, mode):
        if mode not in ("add", "remove", "replace") or not names:
            raise ValueError("Select groups and an assignment mode")
        if not isinstance(job_id, str) or not job_id.isdecimal() or not 0 < int(job_id) < 2**64:
            raise ValueError("A full numeric job ID string is required")
        if self.tcp is None:
            self.connect()
        clients = self.clients()
        groups = {g["name"]: g["clients"] for g in self.groups(clients)}
        if any(name not in groups for name in names):
            raise ValueError("Unknown group")
        members = {c for name in names for c in groups[name]}
        ids = [c.listIdx for c in clients if c.name() in members]
        if not ids:
            raise ValueError("Selected groups have no current clients")
        self.require(self.tcp.jobList_GetInfo(int(job_id)))
        job = self.tcp.jobs.getJobInfo(int(job_id))
        if job is None or str(job.ID) != job_id:
            raise ValueError("Job not found")
        self.require(self.tcp.jobSend_ChangeClientAssignment(
            [int(job_id)], mode in ("add", "replace"), mode in ("remove", "replace"), ids))
        return {"accepted": True, "job_id": job_id, "mode": mode, "clients": sorted(members)}
