"""Relevé de quota par fenêtre, lisible hors d'un run — ticket-558."""
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from tessera.main import app
from tessera.services.quota_registry import QUOTA_REGISTRY, QuotaRegistry
from tessera.services.quota_tracker import QuotaSnapshot, QuotaTracker

NOW = datetime(2026, 10, 24, 12, 0, tzinfo=timezone.utc)


class _Clock:
    """Horloge simulée : le test avance le temps à la main."""

    def __init__(self) -> None:
        self.now = NOW

    def __call__(self) -> datetime:
        return self.now


class _Info:
    def __init__(self, window: str | None, utilization: float, resets_at: float | None) -> None:
        self.status = "allowed"
        self.rate_limit_type = window
        self.utilization = utilization
        self.resets_at = resets_at


def _snap(window: str | None, utilization: float, resets_in_h: float | None = 2) -> QuotaSnapshot:
    resets = NOW + timedelta(hours=resets_in_h) if resets_in_h is not None else None
    return QuotaSnapshot("allowed", utilization, window, resets)


@pytest.fixture
def registry() -> tuple[QuotaRegistry, _Clock]:
    clock = _Clock()
    return QuotaRegistry(clock), clock


@pytest.fixture
def clean_global() -> Iterator[None]:
    QUOTA_REGISTRY.clear()
    yield
    QUOTA_REGISTRY.clear()


def test_two_windows_coexist(registry: tuple[QuotaRegistry, _Clock]) -> None:
    reg, _ = registry
    reg.record(_snap("five_hour", 0.4))
    reg.record(_snap("seven_day", 0.7))

    readings = reg.readings()

    assert set(readings) == {"five_hour", "seven_day"}
    assert readings["five_hour"].snapshot.utilization == 0.4
    assert readings["seven_day"].snapshot.utilization == 0.7


def test_a_second_reading_of_the_same_window_replaces_the_first(
    registry: tuple[QuotaRegistry, _Clock],
) -> None:
    reg, clock = registry
    reg.record(_snap("five_hour", 0.4))
    clock.now = NOW + timedelta(minutes=5)
    reg.record(_snap("five_hour", 0.6))

    readings = reg.readings()

    assert list(readings) == ["five_hour"]
    assert readings["five_hour"].snapshot.utilization == 0.6
    assert readings["five_hour"].observed_at == clock.now


def test_an_expired_reading_is_not_returned(registry: tuple[QuotaRegistry, _Clock]) -> None:
    reg, clock = registry
    reg.record(_snap("five_hour", 0.9, resets_in_h=1))
    reg.record(_snap("seven_day", 0.5, resets_in_h=48))
    assert set(reg.readings()) == {"five_hour", "seven_day"}

    clock.now = NOW + timedelta(hours=1, seconds=1)

    assert set(reg.readings()) == {"seven_day"}


def test_a_reading_without_resets_at_stays_until_replaced(
    registry: tuple[QuotaRegistry, _Clock],
) -> None:
    reg, clock = registry
    reg.record(_snap("five_hour", 0.3, resets_in_h=None))
    clock.now = NOW + timedelta(days=30)

    assert "five_hour" in reg.readings()


def test_a_reading_without_window_is_kept_as_unknown(
    registry: tuple[QuotaRegistry, _Clock],
) -> None:
    reg, _ = registry
    reg.record(_snap(None, 0.5))

    readings = reg.readings()

    assert list(readings) == ["unknown"]
    assert "five_hour" not in readings
    assert "seven_day" not in readings


def test_none_is_ignored(registry: tuple[QuotaRegistry, _Clock]) -> None:
    reg, _ = registry
    reg.record(None)

    assert reg.readings() == {}


def test_tracker_observe_feeds_the_registry(clean_global: None) -> None:
    tracker = QuotaTracker()
    future = (datetime.now(timezone.utc) + timedelta(hours=3)).timestamp()

    tracker.observe(_Info("five_hour", 0.5, future))

    assert tracker.snapshot is not None
    assert set(QUOTA_REGISTRY.readings()) == {"five_hour"}


def test_endpoint_is_empty_without_reading(clean_global: None) -> None:
    response = TestClient(app).get("/api/v1/usage/quota")

    assert response.status_code == 200
    assert response.json() == {"windows": {}}


def test_endpoint_returns_each_window(clean_global: None) -> None:
    tracker = QuotaTracker()
    soon = (datetime.now(timezone.utc) + timedelta(hours=2)).timestamp()
    later = (datetime.now(timezone.utc) + timedelta(days=3)).timestamp()
    tracker.observe(_Info("five_hour", 0.42, soon))
    tracker.observe(_Info("seven_day", 0.7, later))

    body = TestClient(app).get("/api/v1/usage/quota").json()

    assert set(body["windows"]) == {"five_hour", "seven_day"}
    five = body["windows"]["five_hour"]
    assert five["status"] == "allowed"
    assert five["utilization"] == 0.42
    assert five["resets_at"] is not None
    assert five["observed_at"] is not None
    assert body["windows"]["seven_day"]["utilization"] == 0.7
