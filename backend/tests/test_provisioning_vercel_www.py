"""The www domain of a Vercel project, redirected to the apex — ticket-502."""
import httpx

from tessera.services.provisioning import DnsRecord, StepState, VercelClient, VercelProjectStep
from tests.test_provisioning_vercel import FakeVercel, _client, _ctx

_WWW_CNAME = DnsRecord("CNAME", "www.example.com", "cname.vercel-dns.com")


async def test_adding_the_domain_also_adds_www_redirecting_to_it() -> None:
    fake = FakeVercel(project=True)
    client = _client(fake)
    result = await VercelProjectStep(client).apply(_ctx(client))
    corps = [fake.body(r) for r in fake.calls("POST", "/v10/projects/demo/domains")]
    assert corps == [
        {"name": "example.com"},
        {"name": "www.example.com", "redirect": "example.com", "redirectStatusCode": 308},
    ]
    assert "www.example.com" in result.detail


async def test_www_is_added_even_when_the_apex_is_already_attached() -> None:
    fake = FakeVercel(project=True, domain=True, verified=True, www=False)
    client = _client(fake)
    step = VercelProjectStep(client)
    assert (await step.inspect(_ctx(client))).state is StepState.TODO
    await step.apply(_ctx(client))
    corps = [fake.body(r) for r in fake.calls("POST", "/v10/projects/demo/domains")]
    assert [c["name"] for c in corps] == ["www.example.com"]


async def test_recommended_www_record_joins_wanted_dns() -> None:
    fake = FakeVercel(project=True)
    client = _client(fake)
    ctx = _ctx(client)
    await VercelProjectStep(client).apply(ctx)
    assert _WWW_CNAME in ctx.wanted_dns
    assert ctx.wanted_dns.count(DnsRecord("A", "example.com", "76.76.21.21")) == 1


async def test_inspect_asks_for_the_www_record_when_www_is_attached() -> None:
    fake = FakeVercel(project=True, domain=True)
    client = _client(fake)
    ctx = _ctx(client)
    result = await VercelProjectStep(client).inspect(ctx)
    assert result.state is StepState.SKIPPED
    assert _WWW_CNAME in ctx.wanted_dns


async def test_existing_www_is_neither_recreated_nor_modified() -> None:
    fake = FakeVercel(project=True, domain=True, verified=True, www=True)
    client = _client(fake)
    step = VercelProjectStep(client)
    assert (await step.inspect(_ctx(client))).state is StepState.SKIPPED
    await step.apply(_ctx(client))
    assert fake.calls("POST", "/") == []
    assert [r for r in fake.requests if r.method not in ("GET",)] == []


async def test_declared_www_domain_adds_no_second_www() -> None:
    requetes: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requetes.append(request)
        if request.method == "POST":
            return httpx.Response(200, json={"name": "www.example.com", "verified": True})
        if request.url.path == "/v9/projects/demo":
            return httpx.Response(200, json={"id": "prj_1"})
        if request.url.path.endswith("/config"):
            return httpx.Response(200, json={"misconfigured": False})
        return httpx.Response(404, json={"error": {"code": "not_found"}})

    client = VercelClient("vtok_Q8w2ZkLmN4xPr7", "", httpx.MockTransport(handler))
    ctx = _ctx(client, domain="www.example.com")
    await VercelProjectStep(client).apply(ctx)
    assert all("www.www" not in str(r.url) for r in requetes)
    posts = [r for r in requetes if r.method == "POST"]
    assert len(posts) == 1 and b"redirect" not in posts[0].content
    result = await VercelProjectStep(client).inspect(_ctx(client, domain="www.example.com"))
    assert all("www.www" not in str(r.url) for r in requetes)
    assert result.state is StepState.TODO
