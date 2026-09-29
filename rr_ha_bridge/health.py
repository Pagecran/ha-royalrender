"""Job health based on RR flags and observed changes, not lifetime error totals."""


class HealthTracker:
    def __init__(self, window=300):
        self.window = window
        self.history = {}

    def apply(self, jobs, now):
        present = set()
        for job in jobs:
            key = job["id"]
            present.add(key)
            previous = self.history.get(key)
            recent_at = previous[2] if previous else None
            # First observation is a baseline, not a new error event.
            if previous:
                if job["errors"] > previous[0]:
                    recent_at = now
                elif job["errors"] < previous[0] or job["done"] < previous[1]:
                    recent_at = None  # Reset/requeue.
                elif job["done"] > previous[1]:
                    recent_at = None  # Rendering recovered.
            recent = recent_at is not None and now - recent_at < self.window
            if job["disabled_errors"]:
                health = "blocked"
            elif job["finished"]:
                health = "finished"
            elif job["disabled"]:
                health = "disabled"
            elif recent:
                health = "warning"
            elif job["rendering"]:
                health = "rendering"
            else:
                health = "waiting"
            job["health"] = health
            job["problem"] = health in ("blocked", "warning")
            job["recent_errors"] = recent
            self.history[key] = (job["errors"], job["done"], recent_at)
        self.history = {k: v for k, v in self.history.items() if k in present}
