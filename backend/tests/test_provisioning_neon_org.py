"""Neon calls carry the organization id — ticket-499. A fake Neon behind MockTransport."""
import json

import httpx
import pytest

from tessera.services.provisioning import (
    DatabaseStep,
    NeonClient,
    OnlineConfig,
    ProvisioningContext,
    ServiceError,
    StepState,
)
from tessera.utils.secrets import SecretRegistry

_KEY = "napi_Zk4Lm8Qw2Xr7Vb"
_PASSWORD = "p4ss-Wq9Zt3Lm"
_URI = f"postgresql://owner:{_PASSWORD}@ep-demo.neon.tech/neondb"


class OrgNeon:
    """A Neon that wants ``org_id`` and records every request."""

    def __init__(self, orgs: tuple[str, ...]) -> None:
        self.orgs = orgs
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path.removeprefix("/api/v2")
        if path == "/users/me/organizations":
            return httpx.Response(200, json={"organizations": [{"id": o} for o in self.orgs]})
        if request.method == "POST" and path == "/projects":
            return httpx.Response(201, json={
                "project": {"id": "prj_new"}, "connection_uris": [{"connection_uri": _URI}]})
        if path == "/projects":
            return httpx.Response(200, json={"projects": []})
        return httpx.Response(500, json={"error": {"code": "unexpected_route"}})

    def organization_calls(self) -> int:
        return len([r for r in self.requests if r.url.path.endswith("/organizations")])

    def project_queries(self) -> list[httpx.QueryParams]:
        return [r.url.params for r in self.requests
                if r.method == "GET" and r.url.path.endswith("/projects")]


class FakeEnv:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    async def has_env(self, name: str) -> bool:
        return name in self.values

    async def set_env(self, name: str, value: str) -> None:
        self.values[name] = value


def _client(fake: OrgNeon, org_id: str = "") -> NeonClient:
    return NeonClient(_KEY, httpx.MockTransport(fake), org_id)


async def test_find_projects_sends_the_configured_org_id() -> None:
    fake = OrgNeon(orgs=("org_a", "org_b"))
    await _client(fake, org_id="org_b").find_projects("demo")
    assert fake.project_queries()[0]["org_id"] == "org_b"
    assert fake.organization_calls() == 0


async def test_single_organization_is_read_once_and_used_by_later_calls() -> None:
    fake = OrgNeon(orgs=("org_only",))
    client = _client(fake)
    await client.find_projects("demo")
    await client.create_project("demo")
    assert fake.organization_calls() == 1
    assert fake.project_queries()[0]["org_id"] == "org_only"
    posted = [r for r in fake.requests if r.method == "POST"]
    assert json.loads(posted[0].content)["project"]["org_id"] == "org_only"


async def test_account_without_organization_sends_no_org_id() -> None:
    fake = OrgNeon(orgs=())
    client = _client(fake)
    await client.find_projects("demo")
    await client.create_project("demo")
    assert "org_id" not in fake.project_queries()[0]
    posted = [r for r in fake.requests if r.method == "POST"]
    assert "org_id" not in json.loads(posted[0].content)["project"]


async def test_several_organizations_without_setting_need_a_human() -> None:
    fake = OrgNeon(orgs=("org_a", "org_b"))
    step = DatabaseStep(_client(fake), SecretRegistry())
    ctx = ProvisioningContext("demo", OnlineConfig(domain="example.com"), FakeEnv())
    for result in (await step.inspect(ctx), await step.apply(ctx)):
        assert result.state is StepState.NEEDS_HUMAN
        assert "NEON_ORG_ID" in result.detail
    assert [r for r in fake.requests if r.url.path.endswith("/projects")] == []


async def test_create_project_puts_org_id_in_the_body() -> None:
    fake = OrgNeon(orgs=())
    await _client(fake, org_id="org_a").create_project("demo")
    posted = [r for r in fake.requests if r.method == "POST"]
    assert json.loads(posted[0].content) == {"project": {"name": "demo", "org_id": "org_a"}}


async def test_http_400_detail_carries_the_message_of_neon() -> None:
    message = "org_id is required, you can find it on your organization settings page"

    def refuse(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"code": "", "message": message})

    client = NeonClient(_KEY, httpx.MockTransport(refuse), "org_a")
    with pytest.raises(ServiceError) as erreur:
        await client.find_projects("demo")
    assert "HTTP 400" in str(erreur.value) and message in str(erreur.value)


async def test_message_is_cleaned_of_the_key_urls_and_length() -> None:
    echo = f"bad key {_KEY} for {_URI} " + "x" * 1000

    def refuse(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"message": echo})

    client = NeonClient(_KEY, httpx.MockTransport(refuse), "org_a")
    with pytest.raises(ServiceError) as erreur:
        await client.find_projects("demo")
    texte = str(erreur.value)
    assert _KEY not in texte and _PASSWORD not in texte and len(texte) < 400
