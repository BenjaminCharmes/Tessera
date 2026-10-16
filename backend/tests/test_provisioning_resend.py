"""The Resend steps — ADR-053, ticket-468. Fake APIs behind MockTransport, no network."""
import json
import logging

import httpx
import pytest

from tessera.services.provisioning import (
    DnsRecord,
    OnlineConfig,
    ProvisioningContext,
    ProvisioningPlan,
    ResendClient,
    ResendDomainStep,
    ResendVerifyStep,
    ServiceError,
    StepState,
    VercelClient,
    VercelEnvWriter,
)
from tessera.utils.secrets import SecretRegistry

_TOKEN = "re_adminKey_Zk3Lm9Qw"
_SENDING_KEY = "re_sending_Xp4Tn7Vb"
_RECORDS: list[dict[str, object]] = [
    {"record": "SPF", "name": "send", "type": "MX", "value": "feedback-smtp.example.net",
     "priority": 10, "status": "not_started"},
    {"record": "SPF", "name": "send", "type": "TXT", "value": "v=spf1 include:example.net ~all",
     "status": "not_started"},
    {"record": "DKIM", "name": "resend._domainkey", "type": "TXT", "value": "p=MIGfMA0",
     "status": "not_started"},
]


class FakeResend:
    """A minimal Resend: state in attributes, every request recorded."""

    def __init__(self, domain: str | None = None, key: bool = False,
                 after_verify: str = "pending") -> None:
        self.domain_status = domain
        self.key = key
        self.after_verify = after_verify
        self.requests: list[httpx.Request] = []

    def calls(self, method: str, prefix: str) -> list[httpx.Request]:
        return [r for r in self.requests
                if r.method == method and r.url.path.startswith(prefix)]

    def body(self, request: httpx.Request) -> dict[str, object]:
        loaded: dict[str, object] = json.loads(request.content)
        return loaded

    def _domain(self, with_records: bool) -> dict[str, object]:
        corps: dict[str, object] = {"id": "dom_1", "name": "example.com",
                                    "status": self.domain_status}
        if with_records:
            corps["records"] = _RECORDS
        return corps

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        key, path = request.method, request.url.path
        if key == "GET" and path == "/domains":
            found = [self._domain(False)] if self.domain_status else []
            return httpx.Response(200, json={"object": "list", "data": found})
        if key == "POST" and path == "/domains":
            self.domain_status = "not_started"
            return httpx.Response(201, json=self._domain(True))
        if key == "GET" and path == "/domains/dom_1":
            return httpx.Response(200, json=self._domain(True))
        if key == "POST" and path == "/domains/dom_1/verify":
            self.domain_status = self.after_verify
            return httpx.Response(200, json={"object": "domain", "id": "dom_1"})
        return self._route_keys(request)

    def _route_keys(self, request: httpx.Request) -> httpx.Response:
        key, path = request.method, request.url.path
        if key == "GET" and path == "/api-keys":
            found = [{"id": "key_1", "name": "demo-sending"}] if self.key else []
            return httpx.Response(200, json={"data": found})
        if key == "POST" and path == "/api-keys":
            self.key = True
            return httpx.Response(201, json={"id": "key_1", "token": _SENDING_KEY})
        return httpx.Response(500, json={"name": "unexpected_route"})


class FakeVercelEnv:
    """The env endpoints of Vercel, enough for `VercelEnvWriter`."""

    def __init__(self, envs: tuple[str, ...] = ()) -> None:
        self.envs = list(envs)
        self.requests: list[httpx.Request] = []

    def written(self) -> list[dict[str, object]]:
        posts = [r for r in self.requests if r.method == "POST"]
        return [json.loads(r.content) for r in posts]

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.method == "GET":
            return httpx.Response(200, json={"envs": [{"key": k} for k in self.envs]})
        self.envs.append(str(json.loads(request.content)["key"]))
        return httpx.Response(200, json={})


def _client(fake: FakeResend, token: str = _TOKEN) -> ResendClient:
    return ResendClient(token, httpx.MockTransport(fake))


def _ctx(vercel: FakeVercelEnv, dns_published: bool = False) -> ProvisioningContext:
    writer = VercelEnvWriter(VercelClient("vtok", transport=httpx.MockTransport(vercel)), "demo")
    online = OnlineConfig(domain="example.com", resources=["resend"])
    return ProvisioningContext("demo", online, writer, dns_published=dns_published)


# ------------------------------------------------------------------
# Domain
# ------------------------------------------------------------------


async def test_existing_domain_is_not_recreated() -> None:
    fake, vercel = FakeResend(domain="pending", key=True), FakeVercelEnv(("RESEND_API_KEY",))
    step = ResendDomainStep(_client(fake), SecretRegistry())
    ctx = _ctx(vercel)
    assert (await step.inspect(ctx)).state is StepState.SKIPPED
    assert (await step.apply(ctx)).state is StepState.SKIPPED
    assert fake.calls("POST", "/") == []


async def test_missing_domain_is_created_and_its_dns_records_are_requested() -> None:
    fake, vercel = FakeResend(), FakeVercelEnv()
    ctx = _ctx(vercel)
    step = ResendDomainStep(_client(fake), SecretRegistry())
    assert (await step.inspect(ctx)).state is StepState.TODO
    assert fake.calls("POST", "/") == [] and ctx.wanted_dns == []
    assert (await step.apply(ctx)).state is StepState.DONE
    assert fake.body(fake.calls("POST", "/domains")[0]) == {"name": "example.com"}
    assert ctx.wanted_dns == [
        DnsRecord("MX", "send.example.com", "feedback-smtp.example.net", 10),
        DnsRecord("TXT", "send.example.com", "v=spf1 include:example.net ~all"),
        DnsRecord("TXT", "resend._domainkey.example.com", "p=MIGfMA0"),
    ]


async def test_records_of_an_existing_pending_domain_are_read_once() -> None:
    fake, vercel = FakeResend(domain="pending", key=True), FakeVercelEnv(("RESEND_API_KEY",))
    ctx = _ctx(vercel)
    step = ResendDomainStep(_client(fake), SecretRegistry())
    await step.inspect(ctx)
    await step.apply(ctx)
    assert len(ctx.wanted_dns) == 3


async def test_verified_domain_asks_for_no_dns_record() -> None:
    fake, vercel = FakeResend(domain="verified", key=True), FakeVercelEnv(("RESEND_API_KEY",))
    ctx = _ctx(vercel)
    await ResendDomainStep(_client(fake), SecretRegistry()).apply(ctx)
    assert ctx.wanted_dns == [] and fake.calls("GET", "/domains/") == []


# ------------------------------------------------------------------
# Sending key
# ------------------------------------------------------------------


async def test_created_key_is_limited_to_sending_and_written_to_vercel() -> None:
    fake, vercel = FakeResend(), FakeVercelEnv()
    ctx = _ctx(vercel)
    registry = SecretRegistry()
    await ResendDomainStep(_client(fake), registry).apply(ctx)
    assert fake.body(fake.calls("POST", "/api-keys")[0]) == {
        "name": "demo-sending", "permission": "sending_access", "domain_id": "dom_1"}
    assert vercel.written() == [{
        "key": "RESEND_API_KEY", "value": _SENDING_KEY, "type": "sensitive",
        "target": ["production", "preview"]}]
    assert ctx.changed_env == {"RESEND_API_KEY"}
    assert _SENDING_KEY in registry.valeurs()


async def test_existing_key_without_its_variable_needs_a_human_and_deletes_nothing() -> None:
    fake, vercel = FakeResend(domain="verified", key=True), FakeVercelEnv()
    step = ResendDomainStep(_client(fake), SecretRegistry())
    for action in (step.inspect, step.apply):
        result = await action(_ctx(vercel))
        assert result.state is StepState.NEEDS_HUMAN
        assert "demo-sending" in result.detail
    assert fake.calls("DELETE", "/") == []
    assert fake.calls("POST", "/api-keys") == [] and vercel.written() == []


async def test_existing_key_with_its_variable_is_skipped() -> None:
    fake, vercel = FakeResend(domain="verified", key=True), FakeVercelEnv(("RESEND_API_KEY",))
    result = await ResendDomainStep(_client(fake), SecretRegistry()).apply(_ctx(vercel))
    assert result.state is StepState.SKIPPED
    assert fake.calls("POST", "/api-keys") == [] and vercel.written() == []


async def test_existing_variable_without_key_creates_no_orphan_key() -> None:
    fake, vercel = FakeResend(domain="verified"), FakeVercelEnv(("RESEND_API_KEY",))
    result = await ResendDomainStep(_client(fake), SecretRegistry()).apply(_ctx(vercel))
    assert result.state is StepState.SKIPPED
    assert fake.calls("POST", "/api-keys") == []


async def test_key_response_without_token_fails_without_writing() -> None:
    def no_token(request: httpx.Request) -> httpx.Response:
        return httpx.Response(201, json={"id": "key_1"})

    client = ResendClient(_TOKEN, httpx.MockTransport(no_token))
    with pytest.raises(ServiceError) as erreur:
        await client.create_sending_key("demo-sending", "dom_1")
    assert erreur.value.code == "missing_token"


# ------------------------------------------------------------------
# Verification
# ------------------------------------------------------------------


async def test_verification_is_not_launched_until_dns_is_published() -> None:
    fake, vercel = FakeResend(domain="pending"), FakeVercelEnv()
    step = ResendVerifyStep(_client(fake))
    ctx = _ctx(vercel, dns_published=False)
    assert (await step.inspect(ctx)).state is StepState.PENDING
    assert (await step.apply(ctx)).state is StepState.PENDING
    assert fake.calls("POST", "/") == []


@pytest.mark.parametrize("status, expected", [
    ("verified", StepState.DONE),
    ("pending", StepState.PENDING),
    ("temporary_failure", StepState.PENDING),
    ("failed", StepState.FAILED),
])
async def test_verification_status_maps_to_a_step_state(
    status: str, expected: StepState
) -> None:
    fake = FakeResend(domain="not_started", after_verify=status)
    step = ResendVerifyStep(_client(fake))
    ctx = _ctx(FakeVercelEnv(), dns_published=True)
    assert (await step.inspect(ctx)).state is StepState.TODO
    assert (await step.apply(ctx)).state is expected
    assert len(fake.calls("POST", "/domains/dom_1/verify")) == 1


async def test_verified_domain_is_not_verified_again() -> None:
    fake = FakeResend(domain="verified")
    step = ResendVerifyStep(_client(fake))
    ctx = _ctx(FakeVercelEnv(), dns_published=True)
    assert (await step.inspect(ctx)).state is StepState.SKIPPED
    assert (await step.apply(ctx)).state is StepState.SKIPPED
    assert fake.calls("POST", "/") == []


async def test_verifying_a_missing_domain_needs_a_human() -> None:
    fake = FakeResend()
    ctx = _ctx(FakeVercelEnv(), dns_published=True)
    assert (await ResendVerifyStep(_client(fake)).apply(ctx)).state is StepState.NEEDS_HUMAN
    assert fake.calls("POST", "/") == []


# ------------------------------------------------------------------
# No token, no leak
# ------------------------------------------------------------------


@pytest.mark.parametrize("token", ["", "   "])
async def test_without_token_every_step_needs_a_human_and_sends_nothing(token: str) -> None:
    fake, vercel = FakeResend(), FakeVercelEnv()
    client = _client(fake, token)
    ctx = _ctx(vercel, dns_published=True)
    for step in (ResendDomainStep(client, SecretRegistry()), ResendVerifyStep(client)):
        assert (await step.inspect(ctx)).state is StepState.NEEDS_HUMAN
        assert (await step.apply(ctx)).state is StepState.NEEDS_HUMAN
    assert fake.requests == [] and vercel.requests == []


async def test_token_is_a_bearer_header() -> None:
    fake = FakeResend()
    await _client(fake).find_domain("example.com")
    assert fake.requests[0].headers["Authorization"] == f"Bearer {_TOKEN}"


async def test_service_error_carries_neither_token_nor_echoed_value() -> None:
    echo = f"rejected {_TOKEN}"

    def refuse(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"name": "restricted_api_key", "message": echo})

    client = ResendClient(_TOKEN, httpx.MockTransport(refuse))
    with pytest.raises(ServiceError) as erreur:
        await client.find_domain("example.com")
    texte = str(erreur.value) + repr(erreur.value.args)
    assert "HTTP 403" in texte and "restricted_api_key" in texte and _TOKEN not in texte


async def test_network_failure_becomes_a_service_error_without_detail() -> None:
    def broken(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(f"cannot reach {request.url} with {_TOKEN}")

    client = ResendClient(_TOKEN, httpx.MockTransport(broken))
    with pytest.raises(ServiceError) as erreur:
        await client.find_domain("example.com")
    assert erreur.value.code == "unreachable" and _TOKEN not in str(erreur.value)


async def test_logs_and_results_never_hold_a_token(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    fake, vercel = FakeResend(), FakeVercelEnv()
    registry = SecretRegistry()
    plan = ProvisioningPlan(
        [ResendDomainStep(_client(fake), registry), ResendVerifyStep(_client(fake))],
        secrets=registry,
    )
    sorties = await plan.run(_ctx(vercel))
    vus = [str(r.__dict__) + r.getMessage() for r in caplog.records]
    vus += [o.result.detail for o in sorties]
    assert [o.result.state for o in sorties] == [StepState.DONE, StepState.PENDING]
    for secret in (_TOKEN, _SENDING_KEY):
        assert not any(secret in texte for texte in vus)
