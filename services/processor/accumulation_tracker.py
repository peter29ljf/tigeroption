from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone


class AccumulationTracker:
    """Track same-symbol same-direction large orders within a sliding time window.

    When the same symbol/direction appears 3+ times within the window,
    the caller can apply a score bonus to signal institutional accumulation.
    """

    def __init__(self, window_minutes: int = 60) -> None:
        self._window = timedelta(minutes=window_minutes)
        # key: (symbol, direction) → deque of UTC datetimes
        self._buckets: dict[tuple[str, str], deque[datetime]] = defaultdict(deque)

    def record_and_count(self, symbol: str, direction: str, ts: datetime | None = None) -> int:
        """Record a flow event and return the count of events in the window."""
        if ts is None:
            ts = datetime.now(timezone.utc)
        elif ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        key = (symbol.upper(), direction.upper())
        q = self._buckets[key]
        cutoff = ts - self._window
        while q and q[0] < cutoff:
            q.popleft()
        q.append(ts)
        return len(q)


def accumulation_bonus(count: int) -> int:
    """Score bonus for consecutive same-direction flows (3rd+ within 60 min)."""
    if count < 3:
        return 0
    return min((count - 2) * 5, 15)
