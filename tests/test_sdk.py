from types import SimpleNamespace as NS
from unittest.mock import Mock

import pytest

from rr_ha_bridge.sdk import RoyalRenderSDK


def adapter():
    sdk = RoyalRenderSDK(None)
    # Deliberately non-contiguous global IDs, unrelated to list positions.
    clients = [NS(name=lambda: "node-a", listIdx=7), NS(name=lambda: "node-b", listIdx=42)]
    sdk.tcp = Mock()
    sdk.tcp.clientGetList.return_value = True
    sdk.tcp.clients.count.return_value = 2
    sdk.tcp.clients.at.side_effect = clients.__getitem__
    group = NS(getName=lambda: "CPU", isMember_byGlobalIndex=lambda i: i == 42)
    sdk.tcp.clientGetGroups.return_value = NS(count=1, clientGroup=lambda i: group)
    sdk.tcp.jobs.getJobInfo.return_value = NS(ID=1877000000000000001)
    sdk.lib = NS(_ClientCommand=NS(cDisable=5, cUseWorking=6, cAbortAfterFrameDisable=7))
    return sdk


def test_command_resolves_global_client_id():
    sdk = adapter()
    sdk.machine_command("node-b", "disable")
    sdk.tcp.clientSendCommand.assert_called_once_with([42], 5, "")


@pytest.mark.parametrize("mode,assign,deassign", [("add", True, False), ("remove", False, True), ("replace", True, True)])
def test_group_modes_and_64_bit_ids(mode, assign, deassign):
    sdk = adapter()
    sdk.assign_groups("1877000000000000001", ["CPU"], mode)
    sdk.tcp.jobSend_ChangeClientAssignment.assert_called_once_with(
        [1877000000000000001], assign, deassign, [42])


@pytest.mark.parametrize("groups", [[], ["missing"]])
def test_bad_group_cannot_mutate_job(groups):
    sdk = adapter()
    with pytest.raises(ValueError):
        sdk.assign_groups("1877000000000000001", groups, "replace")
    sdk.tcp.jobSend_ChangeClientAssignment.assert_not_called()


def test_unknown_client_cannot_mutate_farm():
    sdk = adapter()
    with pytest.raises(ValueError):
        sdk.machine_command("missing", "disable")
    sdk.tcp.clientSendCommand.assert_not_called()


def test_missing_job_cannot_assign_clients():
    sdk = adapter()
    sdk.tcp.jobs.getJobInfo.return_value = None
    with pytest.raises(ValueError):
        sdk.assign_groups("1877000000000000001", ["CPU"], "add")
    sdk.tcp.jobSend_ChangeClientAssignment.assert_not_called()
