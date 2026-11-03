"""Last quota reading of each rate-limit window, kept for the whole process — ticket-558.

`QuotaTracker` lives and dies with one provider, so with one run, and keeps a
single reading whatever the window. The day board needs the session (5 h) and
the week side by side, outside any run. This registry sits at process level, like
`RUN_REGISTRY` (ADR-008): nothing in the orchestrator, which is rebuilt per request.

Nothing is persisted. The SDK only emits a reading when the state changes, so
"no reading" is the nominal case, and an expired reading says nothing either:
once `resets_at` has passed, the window has started over and what it held is
unknown, not "plenty left".
"""
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # `QuotaTracker` inscrit ses relevés ici : l'import à l'exécution serait circulaire.
    from tessera.services.quota_tracker import QuotaSnapshot

# Un relevé sans fenêtre garde sa place, mais sous une clé qui ne se confond
# avec aucune fenêtre réelle : afficher « five_hour » à l'aveugle serait faux.
UNKNOWN_WINDOW = "unknown"


@dataclass(frozen=True)
class QuotaReading:
    """A snapshot and the instant it was read."""

    snapshot: "QuotaSnapshot"
    observed_at: datetime


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class QuotaRegistry:
    """Last reading per window; a newer reading of a window replaces the older."""

    def __init__(self, clock: Callable[[], datetime] = _utc_now) -> None:
        self._clock = clock
        self._readings: dict[str, QuotaReading] = {}

    def record(self, snapshot: "QuotaSnapshot | None") -> None:
        """Keep `snapshot` under its window; None is ignored."""
        if snapshot is None:
            return
        window = snapshot.window or UNKNOWN_WINDOW
        self._readings[window] = QuotaReading(snapshot, self._clock())

    def readings(self) -> dict[str, QuotaReading]:
        """Readings whose window has not started over, by window name."""
        now = self._clock()
        live: dict[str, QuotaReading] = {}
        for window, reading in list(self._readings.items()):
            resets_at = reading.snapshot.resets_at
            if resets_at is not None and resets_at <= now:
                del self._readings[window]
                continue
            live[window] = reading
        return live

    def clear(self) -> None:
        self._readings.clear()


QUOTA_REGISTRY = QuotaRegistry()
