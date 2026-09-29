import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "job_filter", Path(__file__).parents[1] / "custom_components/royalrender/job_filter.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_history_and_active_jobs_are_separate():
    now = 2_000_000_000
    old = now - 11 * 86400
    recent = now - 86400

    def job(id, submitted, **kwargs):
        return {"id": id, "submitted_at": submitted, "rendering": False,
                "disabled_errors": False, "finished": True, "disabled": False,
                "problem": False, "health": "finished", **kwargs}

    data = {"jobs": [
        job("old_finished", old), job("recent_finished", recent),
        job("old_rendering", old, finished=False, rendering=True, health="rendering"),
        job("old_waiting", old, finished=False, health="waiting"),
        job("old_blocked", old, finished=False, disabled=True, disabled_errors=True,
            problem=True, health="blocked"),
        job("old_disabled", old, finished=False, disabled=True, health="disabled"),
        job("no_date_finished", None),
        job("boundary", now - 10 * 86400),
    ], "summary": {"machines_rendering": 1}}
    result = module.filter_snapshot(data, 10, now)
    assert {j["id"] for j in result["jobs"]} == {
        "recent_finished", "old_rendering", "old_waiting", "old_blocked", "boundary"}
    assert result["jobs"][0]["id"] == "recent_finished"
    assert result["summary"]["jobs_problem"] == 1
    assert len(data["jobs"]) == 8  # Input is not modified.
    active = module.filter_snapshot(data, 0, now)
    assert {j["id"] for j in active["jobs"]} == {"old_rendering", "old_waiting", "old_blocked"}
