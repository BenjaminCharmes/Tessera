"""The DNS step — ADR-053, ticket-469. A fake Cloudflare behind MockTransport, no network."""
import json
import re

import httpx

from tessera.services.provisioning import (
    CloudflareClient,
    DnsRecord,
    DnsStep,
    OnlineConfig,
    ProvisioningContext,
    ProvisioningPlan,
    ServiceError,
    StepState,
)
from tessera.utils.secrets import SecretRegistry

_TOKEN = "cf_Zk4Lm8Qw2Xr7Vb"
_A = DnsRecord("A", "example.com", "76.76.21.21")
_TXT = DnsRecord("TXT", "_vercel.example.com", "vc-domain-verify=example.com,abc123")


class FakeCloudflare:
    """A minimal Cloudflare: one zone, its records, every request recorded."""

    def __init__(self, zones: tuple[str, ...] = ("example.com",),
                 records: tuple[dict[str, str], ...] = ()) -> None:
        self.zones = {f"zone_{i}": name for i, name in enumerate(zones)}
        self.records = [dict(r) for r in records]
        self.requests: list[httpx.Request] = []

    def calls(self, method: str) -> list[httpx.Request]:
        return [r for r in self.requests if r.method == method]

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path.removeprefix("/client/v4")
        if request.method == "GET" and path == "/zones":
            wanted = request.url.params["name"]
            found = [{"id": i, "name": n} for i, n in self.zones.items() if n == wanted]
            return httpx.Response(200, json={"success": True, "result": found})
        if re.fullmatch(r"/zones/[^/]+/dns_records", path):
            return self._records(request)
        return httpx.Response(404, json={"errors": [{"code": 7003}]})

    def _records(self, request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            self.records.append(json.loads(request.content))
            return httpx.Response(200, json={"success": True, "result": {}})
        if request.method != "GET":
            return httpx.Response(405, json={"errors": [{"code": 1}]})
        params = request.url.params
        found = [r for r in self.records
                 if r["type"] == params["type"] and r["name"] == params["name"]]
        return httpx.Response(200, json={
            "success": True, "result": found, "result_info": {"page": 1, "total_pages": 1}})


class NoEnv:
    """The Vercel side is irrelevant to this step."""

    async def has_env(self, name: str) -> bool:
        return False

    async def set_env(self, name: str, value: str) -> None:
        raise AssertionError("the DNS step never writes a variable")


def _ctx(*wanted: DnsRecord, resources: tuple[str, ...] = ("dns",),
         domain: str = "example.com") -> ProvisioningContext:
    online = OnlineConfig.model_validate({"domain": domain, "resources": list(resources)})
    return ProvisioningContext("demo", online, NoEnv(), wanted_dns=list(wanted))


def _step(fake: FakeCloudflare, token: str = _TOKEN) -> DnsStep:
    return DnsStep(CloudflareClient(token, httpx.MockTransport(fake)))


def _record(kind: str, name: str, content: str) -> dict[str, str]:
    return {"type": kind, "name": name, "content": content}


async def test_zone_absent_from_cloudflare_needs_a_human_and_creates_nothing() -> None:
    fake = FakeCloudflare(zones=("other.org",))
    ctx = _ctx(_A)
    result = await _step(fake).apply(ctx)
    assert result.state is StepState.NEEDS_HUMAN
    assert "example.com" in result.detail and "76.76.21.21" in result.detail
    assert fake.calls("POST") == []
    assert ctx.dns_published is False


async def test_identical_record_is_ignored_and_missing_one_is_created_unproxied() -> None:
    fake = FakeCloudflare(records=(_record("A", "example.com", "76.76.21.21"),))
    ctx = _ctx(_A, _TXT)
    result = await _step(fake).apply(ctx)
    assert result.state is StepState.DONE
    creations = [json.loads(r.content) for r in fake.calls("POST")]
    assert len(creations) == 1
    assert creations[0]["type"] == "TXT" and creations[0]["name"] == "_vercel.example.com"
    assert creations[0]["content"] == _TXT.content
    assert creations[0]["proxied"] is False
    assert ctx.dns_published is True


async def test_mx_record_is_created_with_its_priority() -> None:
    fake = FakeCloudflare()
    mx = DnsRecord("MX", "send.example.com", "feedback-smtp.us-east-1.amazonses.com", 10)
    result = await _step(fake).apply(_ctx(mx))
    assert result.state is StepState.DONE
    creations = [json.loads(r.content) for r in fake.calls("POST")]
    assert creations[0]["type"] == "MX" and creations[0]["priority"] == 10


async def test_record_without_priority_sends_no_priority_field() -> None:
    fake = FakeCloudflare()
    await _step(fake).apply(_ctx(_A))
    creations = [json.loads(r.content) for r in fake.calls("POST")]
    assert "priority" not in creations[0]


async def test_same_type_and_name_with_another_content_needs_a_human_without_writing() -> None:
    fake = FakeCloudflare(records=(_record("A", "example.com", "203.0.113.7"),))
    ctx = _ctx(_A, _TXT)
    result = await _step(fake).apply(ctx)
    assert result.state is StepState.NEEDS_HUMAN
    assert "203.0.113.7" in result.detail
    # Même l'enregistrement manquant n'est pas créé : l'étape s'arrête avant d'écrire.
    assert fake.calls("POST") == []
    assert len(fake.records) == 1
    assert ctx.dns_published is False


async def test_no_delete_or_update_is_ever_sent() -> None:
    conflict = FakeCloudflare(records=(_record("A", "example.com", "203.0.113.7"),))
    mixed = FakeCloudflare(records=(_record("A", "example.com", "76.76.21.21"),))
    await _step(conflict).apply(_ctx(_A))
    await _step(mixed).apply(_ctx(_A, _TXT))
    await _step(mixed).inspect(_ctx(_A, _TXT))
    sent = {r.method for fake in (conflict, mixed) for r in fake.requests}
    assert sent <= {"GET", "POST"}


async def test_without_token_the_step_is_manual_and_lists_the_records() -> None:
    fake = FakeCloudflare()
    ctx = _ctx(_A, _TXT)
    for action in (_step(fake, token="").inspect, _step(fake, token="  ").apply):
        result = await action(ctx)
        assert result.state is StepState.MANUAL
        assert "A example.com 76.76.21.21" in result.detail
        assert f"TXT _vercel.example.com {_TXT.content}" in result.detail
    assert fake.requests == []


async def test_dns_not_declared_is_manual_and_lists_the_records() -> None:
    fake = FakeCloudflare()
    result = await _step(fake).apply(_ctx(_A, resources=("vercel",)))
    assert result.state is StepState.MANUAL
    assert "A example.com 76.76.21.21" in result.detail
    assert fake.requests == []


async def test_dns_published_only_when_every_requested_record_exists() -> None:
    fake = FakeCloudflare(records=(_record("A", "example.com", "76.76.21.21"),))
    partial = _ctx(_A, _TXT)
    result = await _step(fake).inspect(partial)
    assert (result.state, partial.dns_published) == (StepState.TODO, False)
    complete = _ctx(_A)
    result = await _step(fake).inspect(complete)
    assert (result.state, complete.dns_published) == (StepState.SKIPPED, True)
    await _step(fake).apply(partial)
    assert partial.dns_published is True


async def test_inspect_never_writes() -> None:
    fake = FakeCloudflare()
    result = await _step(fake).inspect(_ctx(_A))
    assert result.state is StepState.TODO
    assert fake.calls("POST") == []


async def test_nothing_requested_publishes_nothing() -> None:
    fake = FakeCloudflare()
    ctx = _ctx()
    result = await _step(fake).apply(ctx)
    assert result.state is StepState.SKIPPED
    assert ctx.dns_published is False
    assert fake.requests == []


async def test_quoted_txt_and_relative_names_match_the_existing_record() -> None:
    fake = FakeCloudflare(records=(_record("TXT", "send.example.com", '"v=spf1 include:x.net ~all"'),))
    wanted = DnsRecord("TXT", "send", "v=spf1 include:x.net ~all")
    ctx = _ctx(wanted)
    result = await _step(fake).apply(ctx)
    assert result.state is StepState.SKIPPED
    assert ctx.dns_published is True


async def test_zone_of_a_subdomain_is_found_in_its_parent() -> None:
    fake = FakeCloudflare()
    wanted = DnsRecord("CNAME", "app.example.com", "cname.vercel-dns.com")
    result = await _step(fake).apply(_ctx(wanted, domain="app.example.com"))
    assert result.state is StepState.DONE
    assert [json.loads(r.content)["name"] for r in fake.calls("POST")] == ["app.example.com"]


async def test_api_failure_is_failed_with_status_and_code_only() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        body = {"errors": [{"code": 9109, "message": f"bad token {_TOKEN}"}]}
        return httpx.Response(403, json=body)

    step = DnsStep(CloudflareClient(_TOKEN, httpx.MockTransport(refuse)))
    plan = ProvisioningPlan([step], secrets=SecretRegistry())
    outcomes = await plan.run(_ctx(_A))
    assert outcomes[0].result.state is StepState.FAILED
    assert _TOKEN not in outcomes[0].result.detail
    assert "9109" in outcomes[0].result.detail


async def test_client_error_carries_no_token() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"errors": [{"code": 10000, "message": _TOKEN}]})

    client = CloudflareClient(_TOKEN, httpx.MockTransport(refuse))
    try:
        await client.find_zones("example.com")
    except ServiceError as error:
        assert _TOKEN not in str(error)
    else:
        raise AssertionError("a 401 must raise")
