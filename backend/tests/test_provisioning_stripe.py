"""The Stripe step — ADR-053, ticket-470. A fake Stripe behind MockTransport, no network."""
import json
import logging
from typing import Optional
from urllib.parse import parse_qs

import httpx
import pytest

from tessera.services.pipeline_events import OrchestratorEvent
from tessera.services.provisioning import (
    OnlineConfig,
    ProvisioningContext,
    ProvisioningPlan,
    ServiceError,
    StepResult,
    StepState,
    StripeClient,
    StripeConfig,
    StripeStep,
)
from tessera.utils.secrets import SecretRegistry

_TEST_KEY = "rk_test_Ab12Cd34Ef56Gh78"
_LIVE_KEY = "rk_live_Zq98Xw76Vu54Ts32"
_SECRET = "whsec_Qm7Lp2Vx9Rt4Bn6"
_URL = "https://example.com/api/hook"
_EVENTS = ["checkout.session.completed", "invoice.paid"]


class FakeStripe:
    """A minimal Stripe: products, prices and webhooks, every request recorded."""

    def __init__(
        self,
        products: tuple[dict[str, object], ...] = (),
        prices: tuple[dict[str, object], ...] = (),
        webhooks: tuple[str, ...] = (),
    ) -> None:
        self.products = list(products)
        self.prices = list(prices)
        self.webhooks = [{"id": f"we_{i}", "url": url} for i, url in enumerate(webhooks)]
        self.requests: list[httpx.Request] = []

    def calls(self, method: str, path: str) -> list[httpx.Request]:
        return [r for r in self.requests if r.method == method and r.url.path == path]

    def form(self, method: str, path: str) -> dict[str, list[str]]:
        return parse_qs(self.calls(method, path)[0].content.decode())

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        route = (request.method, request.url.path)
        if route == ("GET", "/v1/products"):
            return httpx.Response(200, json={"data": self.products, "has_more": False})
        if route == ("GET", "/v1/prices"):
            wanted = request.url.params["lookup_keys[]"]
            data = [p for p in self.prices if p["lookup_key"] == wanted]
            return httpx.Response(200, json={"data": data})
        if route == ("GET", "/v1/webhook_endpoints"):
            return httpx.Response(200, json={"data": self.webhooks, "has_more": False})
        if route == ("POST", "/v1/products"):
            return httpx.Response(200, json={"id": "prod_new"})
        if route == ("POST", "/v1/prices"):
            return httpx.Response(200, json={"id": "price_new"})
        if route == ("POST", "/v1/webhook_endpoints"):
            return httpx.Response(200, json={"id": "we_new", "secret": _SECRET})
        return httpx.Response(404, json={"error": {"code": "resource_missing"}})


class FakeEnv:
    """The Vercel side: what is written, and optionally a failure that echoes the value."""

    def __init__(self, present: tuple[str, ...] = ("STRIPE_SECRET_KEY",),
                 fail_echoing: bool = False) -> None:
        self.values: dict[str, str] = {name: "hidden" for name in present}
        self.writes: list[str] = []
        self.checks: list[str] = []
        self.fail_echoing = fail_echoing

    async def has_env(self, name: str) -> bool:
        self.checks.append(name)
        return name in self.values

    async def set_env(self, name: str, value: str) -> None:
        if self.fail_echoing:
            body = json.dumps({"error": {"code": "bad_request", "message": f"rejected {value}"}})
            raise ServiceError.from_response("vercel", 400, body)
        self.values[name] = value
        self.writes.append(name)


def _client(fake: FakeStripe, key: str = _TEST_KEY) -> StripeClient:
    return StripeClient(key, httpx.MockTransport(fake))


def _ctx(
    env: FakeEnv,
    mode: str = "test",
    product: Optional[str] = None,
    price_cents: Optional[int] = None,
) -> ProvisioningContext:
    stripe = StripeConfig.model_validate({
        "webhook_path": "/api/hook", "events": _EVENTS,
        "product": product, "price_cents": price_cents, "mode": mode,
    })
    online = OnlineConfig(domain="example.com", resources=["stripe"], stripe=stripe)
    return ProvisioningContext("demo", online, env)


def _step(client: StripeClient) -> StripeStep:
    return StripeStep(client, SecretRegistry())


async def test_live_key_without_live_mode_fails_before_any_request() -> None:
    fake, env = FakeStripe(), FakeEnv()
    step = _step(_client(fake, _LIVE_KEY))
    for result in (await step.inspect(_ctx(env)), await step.apply(_ctx(env))):
        assert result.state is StepState.FAILED and _LIVE_KEY not in result.detail
        assert fake.requests == [] and env.checks == [] and env.writes == []


async def test_live_key_passes_when_the_project_declares_live_mode() -> None:
    fake, env = FakeStripe(), FakeEnv()
    result = await _step(_client(fake, _LIVE_KEY)).apply(_ctx(env, mode="live"))
    assert result.state is StepState.DONE and env.writes == ["STRIPE_WEBHOOK_SECRET"]


async def test_test_key_with_live_mode_fails_without_request() -> None:
    fake, env = FakeStripe(), FakeEnv()
    result = await _step(_client(fake, _TEST_KEY)).apply(_ctx(env, mode="live"))
    assert result.state is StepState.FAILED
    assert fake.requests == [] and env.writes == []


async def test_publishable_key_needs_a_human_naming_the_expected_keys_without_the_value() -> None:
    publishable = "pk_test_Zz11Yy22Xx33Ww44"
    fake, env = FakeStripe(), FakeEnv()
    step = _step(_client(fake, publishable))
    for result in (await step.inspect(_ctx(env)), await step.apply(_ctx(env))):
        assert result.state is StepState.NEEDS_HUMAN
        assert "rk_test_" in result.detail and "pk_" in result.detail
        assert "restart" in result.detail
        assert publishable not in result.detail and "Zz11Yy22" not in result.detail
    assert fake.requests == [] and env.writes == []


class _Later:
    """A step after Stripe, to see whether the plan reaches it."""

    name = "later"

    def __init__(self) -> None:
        self.applied = False

    async def inspect(self, ctx: ProvisioningContext) -> StepResult:
        return StepResult(StepState.TODO, "missing")

    async def apply(self, ctx: ProvisioningContext) -> StepResult:
        self.applied = True
        return StepResult(StepState.DONE, "later done")


@pytest.mark.parametrize("key", ["pk_test_Zz11Yy22Xx33Ww44", ""])
async def test_unusable_or_absent_key_lets_the_next_steps_run(key: str) -> None:
    later = _Later()
    plan = ProvisioningPlan([_step(_client(FakeStripe(), key)), later])

    outcomes = await plan.run(_ctx(FakeEnv()))

    assert [o.step for o in outcomes] == ["stripe", "later"]
    assert outcomes[0].result.state is StepState.NEEDS_HUMAN
    assert outcomes[1].result.state is StepState.DONE and later.applied


async def test_network_error_stays_failed_and_stops_the_plan() -> None:
    def broken(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("unreachable")

    later = _Later()
    stripe = StripeStep(StripeClient(_TEST_KEY, httpx.MockTransport(broken)), SecretRegistry())

    outcomes = await ProvisioningPlan([stripe, later]).run(_ctx(FakeEnv()))

    assert [o.step for o in outcomes] == ["stripe"]
    assert outcomes[0].result.state is StepState.FAILED and not later.applied


async def test_existing_product_and_price_are_neither_recreated_nor_modified() -> None:
    fake = FakeStripe(
        products=({"id": "prod_other", "metadata": {}},
                  {"id": "prod_1", "metadata": {"tessera_project": "demo"}}),
        prices=({"id": "price_1", "lookup_key": "tessera_demo", "unit_amount": 500},),
        webhooks=(_URL,),
    )
    env = FakeEnv(present=("STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET"))
    result = await _step(_client(fake)).apply(_ctx(env, product="Pass", price_cents=900))
    assert result.state is StepState.SKIPPED
    assert [r.method for r in fake.requests] == ["GET", "GET", "GET"]
    assert env.writes == []


async def test_product_and_price_are_created_when_declared_and_missing() -> None:
    fake, env = FakeStripe(webhooks=(_URL,)), FakeEnv(present=("STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET"))
    result = await _step(_client(fake)).apply(_ctx(env, product="Pass", price_cents=900))
    assert result.state is StepState.DONE
    assert fake.form("POST", "/v1/products") == {"name": ["Pass"], "metadata[tessera_project]": ["demo"]}
    price = fake.form("POST", "/v1/prices")
    assert price["product"] == ["prod_new"] and price["unit_amount"] == ["900"]
    assert price["lookup_key"] == ["tessera_demo"] and price["currency"] == ["eur"]


async def test_nothing_but_the_webhook_is_created_when_no_product_is_declared() -> None:
    fake, env = FakeStripe(), FakeEnv()
    await _step(_client(fake)).apply(_ctx(env))
    assert fake.calls("GET", "/v1/products") == [] and fake.calls("GET", "/v1/prices") == []
    assert fake.calls("POST", "/v1/products") == [] and fake.calls("POST", "/v1/prices") == []


async def test_price_without_product_fails_without_request() -> None:
    fake, env = FakeStripe(), FakeEnv()
    result = await _step(_client(fake)).apply(_ctx(env, price_cents=900))
    assert result.state is StepState.FAILED and fake.requests == []


async def test_missing_webhook_is_created_and_its_secret_written_to_vercel() -> None:
    fake, env = FakeStripe(webhooks=("https://example.com/other",)), FakeEnv()
    ctx = _ctx(env)
    result = await _step(_client(fake)).apply(ctx)
    assert result.state is StepState.DONE
    form = fake.form("POST", "/v1/webhook_endpoints")
    assert form["url"] == [_URL] and form["enabled_events[]"] == _EVENTS
    assert env.values["STRIPE_WEBHOOK_SECRET"] == _SECRET and ctx.changed_env == {"STRIPE_WEBHOOK_SECRET"}


async def test_inspect_reads_without_creating_or_writing() -> None:
    fake, env = FakeStripe(), FakeEnv()
    result = await _step(_client(fake)).inspect(_ctx(env, product="Pass", price_cents=900))
    assert result.state is StepState.TODO
    assert {r.method for r in fake.requests} == {"GET"} and env.writes == []


async def test_existing_webhook_without_its_variable_needs_a_human_and_deletes_nothing() -> None:
    fake, env = FakeStripe(webhooks=(_URL,)), FakeEnv()
    step = _step(_client(fake))
    for result in (await step.inspect(_ctx(env)), await step.apply(_ctx(env))):
        assert result.state is StepState.NEEDS_HUMAN
        assert "we_0" in result.detail and "STRIPE_WEBHOOK_SECRET" in result.detail
    assert all(r.method == "GET" for r in fake.requests) and env.writes == []


async def test_variable_without_webhook_needs_a_human_instead_of_losing_a_secret() -> None:
    fake = FakeStripe()
    env = FakeEnv(present=("STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET"))
    result = await _step(_client(fake)).apply(_ctx(env))
    assert result.state is StepState.NEEDS_HUMAN
    assert fake.calls("POST", "/v1/webhook_endpoints") == [] and env.writes == []


async def test_missing_site_key_in_vercel_needs_a_human_and_writes_nothing() -> None:
    fake, env = FakeStripe(), FakeEnv(present=())
    step = _step(_client(fake))
    for result in (await step.inspect(_ctx(env)), await step.apply(_ctx(env))):
        assert result.state is StepState.NEEDS_HUMAN and "STRIPE_SECRET_KEY" in result.detail
    assert fake.requests == [] and env.writes == []


async def test_without_key_the_step_is_manual_or_needs_a_human() -> None:
    fake = FakeStripe()
    present = FakeEnv(present=("STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET"))
    assert (await _step(_client(fake, " ")).apply(_ctx(present))).state is StepState.MANUAL
    result = await _step(_client(fake, "")).apply(_ctx(FakeEnv()))
    assert result.state is StepState.NEEDS_HUMAN and "STRIPE_API_KEY" in result.detail
    assert not result.stops_plan
    assert fake.requests == []


async def test_service_error_and_network_failure_carry_no_key_or_secret() -> None:
    echo = f"bad {_TEST_KEY} {_SECRET}"

    def refuse(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"code": "invalid_key", "message": echo}})

    def broken(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(f"cannot reach {request.url} with {_TEST_KEY}")

    for handler in (refuse, broken):
        with pytest.raises(ServiceError) as erreur:
            await StripeClient(_TEST_KEY, httpx.MockTransport(handler)).find_webhooks(_URL)
        texte = str(erreur.value) + repr(erreur.value.args)
        assert _TEST_KEY not in texte and _SECRET not in texte


async def test_key_and_secret_appear_in_no_log_event_result_or_failure(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    events: list[OrchestratorEvent] = []

    async def emit(event: OrchestratorEvent) -> None:
        events.append(event)

    registry = SecretRegistry()
    for env in (FakeEnv(), FakeEnv(fail_echoing=True)):
        step = StripeStep(_client(FakeStripe()), registry)
        outcomes = await ProvisioningPlan([step], emit, registry).run(_ctx(env))
        assert outcomes[0].result.state in (StepState.DONE, StepState.FAILED)
        assert "***" not in outcomes[0].result.detail
    seen = [str(r.__dict__) + r.getMessage() for r in caplog.records] + [str(e) for e in events]
    assert len(events) == 2
    for secret in (_SECRET, _TEST_KEY):
        assert not any(secret in text for text in seen)
    assert _SECRET in registry.valeurs()
