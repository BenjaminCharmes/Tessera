"""Suivi du quota d'abonnement — ticket-054."""
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest

from tessera.services.usage.quota_registry import QUOTA_REGISTRY
from tessera.services.usage.quota_tracker import QuotaSnapshot, QuotaTracker, snapshot_from_rate_limit


@pytest.fixture
def clean_registry() -> Iterator[None]:
    QUOTA_REGISTRY.clear()
    yield
    QUOTA_REGISTRY.clear()


def _unified_info(week: float = 0.56) -> "_FakeRateLimitInfo":
    """Relevé réel du CLI : utilisation de tête vide, usage dans `unifiedWindows`."""
    now = datetime.now(UTC)
    five = (now + timedelta(hours=3)).timestamp()
    seven = (now + timedelta(days=3)).timestamp()
    return _FakeRateLimitInfo(
        status="allowed",
        utilization=None,
        raw={"unifiedWindows": {
            "five_hour": {"utilization": 0.15, "resetsAt": five, "status": "allowed"},
            "seven_day": {"utilization": week, "resetsAt": seven, "status": "allowed"},
        }},
    )


class _FakeRateLimitInfo:
    """Forme du `RateLimitInfo` du SDK, réduite à ce qu'on consomme."""

    def __init__(self, **kwargs: object) -> None:
        self.status = kwargs.get("status", "allowed")
        self.resets_at = kwargs.get("resets_at")
        self.rate_limit_type = kwargs.get("rate_limit_type")
        self.utilization = kwargs.get("utilization")
        self.raw = kwargs.get("raw")


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
    assert snapshot.resets_at.tzinfo is UTC


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
            resets_at=datetime(2026, 9, 16, 12, 0, tzinfo=UTC),
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
    from tessera.services.providers.agent_sdk import ClaudeAgentSDKProvider

    provider = ClaudeAgentSDKProvider()
    assert provider.quota.snapshot is None

    provider.quota.observe(
        _FakeRateLimitInfo(status="allowed_warning", utilization=0.88, rate_limit_type="five_hour")
    )

    assert provider.quota.snapshot is not None
    assert provider.quota.snapshot.utilization == 0.88


# ------------------------------------------------------------------
# Fenêtres du CLI (`raw["unifiedWindows"]`) — ticket-1061
# ------------------------------------------------------------------


def test_observe_reads_both_windows_when_top_level_is_empty(clean_registry: None) -> None:
    QuotaTracker().observe(_unified_info())

    readings = QUOTA_REGISTRY.readings()

    assert set(readings) == {"five_hour", "seven_day"}
    assert readings["five_hour"].snapshot.utilization == 0.15
    assert readings["seven_day"].snapshot.utilization == 0.56
    for reading in readings.values():
        resets_at = reading.snapshot.resets_at
        assert resets_at is not None
        assert resets_at.tzinfo is UTC


def test_tracker_keeps_the_most_used_window_and_is_low_on_the_week(
    clean_registry: None,
) -> None:
    tracker = QuotaTracker()
    tracker.observe(_unified_info(0.56))

    assert tracker.snapshot is not None
    assert tracker.snapshot.window == "seven_day"
    assert tracker.snapshot.utilization == 0.56
    assert tracker.is_low() is False

    tracker.observe(_unified_info(0.92))

    assert tracker.is_low() is True


@pytest.mark.parametrize("raw", [None, {}, {"other": 1}, {"unifiedWindows": "x"}, "texte"])
def test_observe_without_usable_raw_returns_none(clean_registry: None, raw: object) -> None:
    tracker = QuotaTracker()

    assert tracker.observe(_FakeRateLimitInfo(utilization=None, raw=raw)) is None
    assert tracker.snapshot is None
    assert QUOTA_REGISTRY.readings() == {}


def test_a_window_without_numeric_utilization_is_ignored(clean_registry: None) -> None:
    info = _FakeRateLimitInfo(
        utilization=None,
        raw={"unifiedWindows": {
            "five_hour": {"utilization": None, "status": "allowed"},
            "overage": "illisible",
            "seven_day": {"utilization": 0.4},
        }},
    )

    QuotaTracker().observe(info)

    readings = QUOTA_REGISTRY.readings()
    assert set(readings) == {"seven_day"}
    assert readings["seven_day"].snapshot.status == "allowed"


def test_top_level_reading_is_kept_when_its_window_is_not_covered(
    clean_registry: None,
) -> None:
    info = _FakeRateLimitInfo(
        utilization=0.95,
        rate_limit_type="five_hour",
        raw={"unifiedWindows": {"seven_day": {"utilization": 0.3}}},
    )

    QuotaTracker().observe(info)

    assert set(QUOTA_REGISTRY.readings()) == {"five_hour", "seven_day"}
