"""Suivi du quota d'abonnement — ticket-054."""
from datetime import datetime, timezone

from vibe_ide.services.quota_tracker import (
    QuotaSnapshot,
    QuotaTracker,
    snapshot_from_rate_limit,
)


class _FakeRateLimitInfo:
    """Forme du `RateLimitInfo` du SDK, réduite à ce qu'on consomme."""

    def __init__(self, **kwargs: object) -> None:
        self.status = kwargs.get("status", "allowed")
        self.resets_at = kwargs.get("resets_at")
        self.rate_limit_type = kwargs.get("rate_limit_type")
        self.utilization = kwargs.get("utilization")


# ------------------------------------------------------------------
# Normalisation
# ------------------------------------------------------------------


def test_normalise_un_evenement_du_sdk() -> None:
    # La forme du SDK ne doit pas fuiter plus loin : elle dépend de sa version.
    info = _FakeRateLimitInfo(
        status="allowed_warning",
        resets_at=1_757_900_000,
        rate_limit_type="five_hour",
        utilization=0.82,
    )

    snapshot = snapshot_from_rate_limit(info)

    assert snapshot is not None
    assert snapshot.status == "allowed_warning"
    assert snapshot.utilization == 0.82
    assert snapshot.window == "five_hour"
    assert snapshot.resets_at is not None
    assert snapshot.resets_at.tzinfo is timezone.utc


def test_un_evenement_sans_utilisation_est_ignore() -> None:
    # Un provider muet ne doit pas produire un état trompeur à 0 %.
    assert snapshot_from_rate_limit(_FakeRateLimitInfo(utilization=None)) is None


def test_un_evenement_illisible_est_ignore_sans_casser() -> None:
    assert snapshot_from_rate_limit(object()) is None
    assert snapshot_from_rate_limit(None) is None


# ------------------------------------------------------------------
# Tracker
# ------------------------------------------------------------------


def test_le_tracker_demarre_vide() -> None:
    tracker = QuotaTracker()
    assert tracker.snapshot is None
    assert tracker.is_exhausted() is False
    assert tracker.is_low() is False


def test_le_tracker_conserve_le_dernier_etat_connu() -> None:
    tracker = QuotaTracker()
    tracker.record(QuotaSnapshot(status="allowed", utilization=0.30, window="five_hour"))
    tracker.record(QuotaSnapshot(status="allowed_warning", utilization=0.91, window="five_hour"))

    assert tracker.snapshot is not None
    assert tracker.snapshot.utilization == 0.91


def test_un_quota_rejete_est_epuise() -> None:
    tracker = QuotaTracker()
    tracker.record(QuotaSnapshot(status="rejected", utilization=1.0, window="five_hour"))

    assert tracker.is_exhausted() is True
    assert tracker.is_low() is True


def test_un_quota_haut_est_bas_sans_etre_epuise() -> None:
    # Le mode autonome doit s'arrêter *avant* d'être coupé en plein ticket.
    tracker = QuotaTracker(low_threshold=0.90)
    tracker.record(QuotaSnapshot(status="allowed_warning", utilization=0.93, window="five_hour"))

    assert tracker.is_low() is True
    assert tracker.is_exhausted() is False


def test_un_quota_confortable_ne_declenche_rien() -> None:
    tracker = QuotaTracker(low_threshold=0.90)
    tracker.record(QuotaSnapshot(status="allowed", utilization=0.42, window="five_hour"))

    assert tracker.is_low() is False
    assert tracker.is_exhausted() is False


def test_le_tracker_expose_un_etat_serialisable() -> None:
    tracker = QuotaTracker()
    assert tracker.as_event_data() == {"known": False}

    tracker.record(
        QuotaSnapshot(
            status="allowed_warning",
            utilization=0.75,
            window="seven_day",
            resets_at=datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc),
        )
    )
    data = tracker.as_event_data()

    assert data["known"] is True
    assert data["utilization"] == 0.75
    assert data["window"] == "seven_day"
    assert data["status"] == "allowed_warning"
    assert data["resets_at"].startswith("2026-09-16T12:00")


# ------------------------------------------------------------------
# Capture par le provider
# ------------------------------------------------------------------


def test_le_provider_expose_le_dernier_quota_observe() -> None:
    # La capture se fait dans le provider : c'est le seul endroit qui voit les
    # messages du SDK, et la forme du SDK ne doit pas aller plus loin.
    from vibe_ide.services.providers.agent_sdk import ClaudeAgentSDKProvider

    provider = ClaudeAgentSDKProvider()
    assert provider.quota.snapshot is None

    provider.quota.observe(
        _FakeRateLimitInfo(status="allowed_warning", utilization=0.88, rate_limit_type="five_hour")
    )

    assert provider.quota.snapshot is not None
    assert provider.quota.snapshot.utilization == 0.88
