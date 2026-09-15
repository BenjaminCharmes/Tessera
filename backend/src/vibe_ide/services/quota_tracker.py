"""Subscription quota tracking — ticket-054.

ticket-052 bounds the *estimated* spend of a run, computed from tokens and a
price grid. Useful, but it does not measure the right thing: in subscription
mode — the default — the finite resource is not an amount in dollars, it is a
sliding rate-limit window the provider reports.

Without this, a run gets cut mid-flight by a rate limit while every local
ceiling still looks fine, and the user never knows where they stand until they
are blocked.

The SDK's own shape is normalised here, at the boundary, and nowhere else: its
fields move between versions, and an absent event is the nominal case — a
provider that reports nothing leaves the tracker empty rather than breaking.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal, Optional

from vibe_ide.utils.logger import get_logger

_logger = get_logger(__name__)

QuotaStatus = Literal["allowed", "allowed_warning", "rejected"]

# Au-delà de cette proportion consommée, le mode autonome s'arrête entre deux
# tickets. Se faire couper au milieu d'un ticket laisserait son travail non
# commité, ce que l'isolation par branche interdit (ADR-018).
_DEFAULT_LOW_THRESHOLD = 0.90


@dataclass(frozen=True)
class QuotaSnapshot:
    """What is known of the subscription quota at one point in time."""

    status: QuotaStatus
    utilization: float
    window: str | None = None
    resets_at: datetime | None = None


def snapshot_from_rate_limit(info: Any) -> Optional[QuotaSnapshot]:
    """Normalise the SDK's rate-limit payload, or return None if unusable.

    Returns None rather than a zeroed snapshot when the payload carries no
    utilization: an empty tracker says "unknown", a snapshot at 0% would say
    "plenty left", and the second is a lie the UI would display.
    """
    utilization = getattr(info, "utilization", None)
    if not isinstance(utilization, (int, float)):
        return None

    status = getattr(info, "status", "allowed")
    if status not in ("allowed", "allowed_warning", "rejected"):
        status = "allowed"

    resets_at_raw = getattr(info, "resets_at", None)
    resets_at: datetime | None = None
    if isinstance(resets_at_raw, (int, float)):
        try:
            resets_at = datetime.fromtimestamp(resets_at_raw, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            _logger.warning("quota_resets_at_illisible", extra={"value": resets_at_raw})

    window = getattr(info, "rate_limit_type", None)
    return QuotaSnapshot(
        status=status,  # type: ignore[arg-type]
        utilization=float(utilization),
        window=str(window) if window else None,
        resets_at=resets_at,
    )


class QuotaTracker:
    """Keeps the last known quota state for one run.

    Deliberately last-value-wins: the provider reports the current state of a
    sliding window, so an older reading carries no information the newer one
    lacks.
    """

    def __init__(self, low_threshold: float = _DEFAULT_LOW_THRESHOLD) -> None:
        self._low_threshold = low_threshold
        self._snapshot: QuotaSnapshot | None = None

    @property
    def snapshot(self) -> QuotaSnapshot | None:
        return self._snapshot

    def record(self, snapshot: QuotaSnapshot | None) -> None:
        if snapshot is not None:
            self._snapshot = snapshot

    def observe(self, info: Any) -> QuotaSnapshot | None:
        """Normalise and record an SDK payload; returns what was recorded."""
        snapshot = snapshot_from_rate_limit(info)
        self.record(snapshot)
        return snapshot

    def is_exhausted(self) -> bool:
        """True when the provider has actually started refusing."""
        return self._snapshot is not None and self._snapshot.status == "rejected"

    def is_low(self) -> bool:
        """True when little enough is left that starting a ticket is unwise.

        Unknown counts as not low: refusing to work because nothing was
        reported would make a silent provider indistinguishable from an
        exhausted quota.
        """
        if self._snapshot is None:
            return False
        return (
            self._snapshot.status == "rejected"
            or self._snapshot.utilization >= self._low_threshold
        )

    def as_event_data(self) -> dict[str, Any]:
        """Serialisable state for the WebSocket, so the UI need not poll."""
        if self._snapshot is None:
            return {"known": False}
        return {
            "known": True,
            "status": self._snapshot.status,
            "utilization": self._snapshot.utilization,
            "window": self._snapshot.window,
            "resets_at": self._snapshot.resets_at.isoformat()
            if self._snapshot.resets_at
            else None,
        }
