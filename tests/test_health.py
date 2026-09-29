from rr_ha_bridge.health import HealthTracker


def job(**kwargs):
    return {"id": "1877000000000000001", "errors": 4, "done": 1, "total": 10,
            "disabled_errors": False, "disabled": False, "finished": False,
            "rendering": True, **kwargs}


def test_history_recovery_reset_and_expiration():
    tracker = HealthTracker(60)
    j = job()
    tracker.apply([j], 0)
    assert j["health"] == "rendering"  # Old errors do not create a permanent warning.
    j["errors"] += 1
    tracker.apply([j], 1)
    assert j["problem"] and j["health"] == "warning"
    j["done"] += 1
    tracker.apply([j], 2)
    assert not j["problem"]
    j["errors"] += 1
    tracker.apply([j], 3)
    tracker.apply([j], 64)
    assert not j["problem"]
    j["disabled_errors"] = True
    tracker.apply([j], 65)
    assert j["health"] == "blocked"
    j.update(disabled_errors=False, errors=0, done=0, rendering=False)
    tracker.apply([j], 66)
    assert j["health"] == "waiting"
    tracker.apply([], 67)
    assert not tracker.history


def test_finished_and_manual_disable_are_not_incidents():
    tracker = HealthTracker()
    jobs = [job(id="1", finished=True), job(id="2", disabled=True)]
    tracker.apply(jobs, 0)
    assert [j["health"] for j in jobs] == ["finished", "disabled"]
    assert not any(j["problem"] for j in jobs)
