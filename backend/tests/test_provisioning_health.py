"""The health check step — ticket-503. A fake site behind MockTransport, no network, no waiting."""
import json
from pathlib import Path

import httpx

from tessera.services.provisioning import (
    HealthCheckStep,
    OnlineConfig,
    ProvisioningContext,
    StepState,
    load_online_config,
)

_SECRET_BODY = "x" * 500


class FakeSite:
    """A site that answers each request with the next scripted response."""

    def __init__(self, *responses: httpx.Response) -> None:
        self.responses = list(responses)
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if len(self.responses) > 1:
            return self.responses.pop(0)
        return self.responses[0]


class FakeEnv:
    async def has_env(self, name: str) -> bool:
        return True

    async def set_env(self, name: str, value: str) -> None:
        return None


def _ctx(health_path: str | None = None) -> ProvisioningContext:
    online = OnlineConfig(domain="example.com", resources=["vercel"], health_path=health_path)
    return ProvisioningContext(project_id="demo", online=online, env_writer=FakeEnv())


def _step(site: FakeSite, attempts: int = 3) -> tuple[HealthCheckStep, list[float]]:
    pauses: list[float] = []

    async def sleep(seconds: float) -> None:
        pauses.append(seconds)

    transport = httpx.MockTransport(site)
    return HealthCheckStep(transport, attempts=attempts, delay_s=5.0, sleep=sleep), pauses


def test_health_path_is_read_from_the_online_block(tmp_path: Path) -> None:
    bloc = {"online": {"domain": "example.com", "health_path": "/api/health"}}
    (tmp_path / "agents.json").write_text(json.dumps(bloc), encoding="utf-8")
    config = load_online_config(tmp_path)
    assert config is not None
    assert config.health_path == "/api/health"


def test_health_path_is_optional_and_must_be_absolute() -> None:
    assert OnlineConfig(domain="example.com").health_path is None
    try:
        OnlineConfig(domain="example.com", health_path="api/health")
    except ValueError as erreur:
        assert "health_path" in str(erreur)
    else:
        raise AssertionError("a relative health_path must be refused")


async def test_a_healthy_route_makes_the_step_done() -> None:
    site = FakeSite(httpx.Response(200, json={"ok": True}))
    step, pauses = _step(site)
    result = await step.apply(_ctx("/api/health"))
    assert result.state is StepState.DONE
    assert [str(r.url) for r in site.requests] == ["https://example.com/api/health"]
    assert "not checked" not in result.detail
    assert pauses == []


async def test_a_500_makes_the_step_failed_with_the_status_in_the_detail() -> None:
    site = FakeSite(httpx.Response(500, text="relation \"User\" does not exist" + _SECRET_BODY))
    step, pauses = _step(site, attempts=3)
    result = await step.apply(_ctx("/api/health"))
    assert result.state is StepState.FAILED
    assert "500" in result.detail
    assert 'relation "User" does not exist' in result.detail
    assert _SECRET_BODY not in result.detail
    assert len(site.requests) == 3
    assert pauses == [5.0, 5.0]


async def test_without_health_path_the_root_is_checked_and_said_so() -> None:
    site = FakeSite(httpx.Response(200, text="<html></html>"))
    step, _ = _step(site)
    result = await step.apply(_ctx())
    assert result.state is StepState.DONE
    assert str(site.requests[0].url) == "https://example.com/"
    assert "database not checked: declare health_path" in result.detail


async def test_a_deployment_that_answers_late_is_waited_for() -> None:
    site = FakeSite(httpx.Response(404), httpx.Response(502), httpx.Response(200))
    step, pauses = _step(site, attempts=4)
    result = await step.apply(_ctx("/api/health"))
    assert result.state is StepState.DONE
    assert len(site.requests) == 3
    assert pauses == [5.0, 5.0]


async def test_an_unreachable_site_fails_without_leaking_the_network_message() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connect to https://example.com?token=sk_live_secret failed")

    step = HealthCheckStep(httpx.MockTransport(refuse), attempts=2, sleep=_no_sleep)
    result = await step.apply(_ctx("/api/health"))
    assert result.state is StepState.FAILED
    assert "ConnectError" in result.detail
    assert "sk_live_secret" not in result.detail


async def test_inspect_reads_nothing_and_names_the_address() -> None:
    site = FakeSite(httpx.Response(200))
    step, _ = _step(site)
    result = await step.inspect(_ctx("/api/health"))
    assert result.state is StepState.TODO
    assert "https://example.com/api/health" in result.detail
    assert site.requests == []


async def _no_sleep(seconds: float) -> None:
    return None
