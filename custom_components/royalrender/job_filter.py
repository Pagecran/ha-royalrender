"""Keep ongoing jobs and a configurable submission history."""
import time


def filter_snapshot(data, history_days=10, now=None):
    cutoff = (time.time() if now is None else now) - history_days * 86400
    jobs = []
    for job in data["jobs"]:
        active = (job["rendering"] or job["disabled_errors"]
                  or (not job["finished"] and not job["disabled"]))
        submitted = job.get("submitted_at")
        recent = (history_days > 0 and isinstance(submitted, (int, float))
                  and submitted >= cutoff)
        if active or recent:
            jobs.append(job)
    jobs.sort(key=lambda job: job.get("submitted_at") or 0, reverse=True)
    return {**data, "jobs": jobs, "history_days": history_days, "summary": {
        **data["summary"],
        "jobs_rendering": sum(j["rendering"] for j in jobs),
        "jobs_waiting": sum(j["health"] == "waiting" for j in jobs),
        "jobs_problem": sum(j["problem"] for j in jobs),
    }}
