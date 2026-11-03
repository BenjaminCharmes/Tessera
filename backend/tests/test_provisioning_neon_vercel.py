"""A Neon organization managed by Vercel — ticket-500. A fake Neon behind MockTransport."""
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
# Hôte sans point : le garde-fou d'adresses ne doit pas lire l'URI comme un e-mail.
_URI = "postgresql://owner:p4ss-Wq9Zt3Lm@ep-demo/neondb"


class ManagedNeon:
    """A Neon with one organization, no project, and a record of every request."""

    def __init__(self, managed_by: str) -> None:
        self.managed_by = managed_by
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path.removeprefix("/api/v2")
        if path == "/users/me/organizations":
            return httpx.Response(200, json={"organizations": [
                {"id": "org_a", "managed_by": self.managed_by}]})
        if request.method == "POST" and path == "/projects":
            return httpx.Response(201, json={
                "project": {"id": "prj_new"}, "connection_uris": [{"connection_uri": _URI}]})
        if path == "/projects":
            return httpx.Response(200, json={"projects": []})
        return httpx.Response(500, json={"error": {"code": "unexpected_route"}})

    def posts(self) -> list[httpx.Request]:
        return [r for r in self.requests if r.method == "POST"]


class FakeEnv:
    def __init__(self, values: dict[str, str] | None = None) -> None:
        self.values: dict[str, str] = dict(values or {})

    async def has_env(self, name: str) -> bool:
        return name in self.values

    async def set_env(self, name: str, value: str) -> None:
        self.values[name] = value


def _step(fake: ManagedNeon, org_id: str = "") -> DatabaseStep:
    client = NeonClient(_KEY, httpx.MockTransport(fake), org_id)
    return DatabaseStep(client, SecretRegistry())


def _ctx(env: FakeEnv) -> ProvisioningContext:
    return ProvisioningContext("kadoomi", OnlineConfig(domain="example.com"), env)


@pytest.mark.parametrize("org_id", ["", "org_a"])
async def test_vercel_managed_organization_without_project_needs_a_human(org_id: str) -> None:
    fake = ManagedNeon("vercel")
    step, ctx = _step(fake, org_id), _ctx(FakeEnv())
    for result in (await step.inspect(ctx), await step.apply(ctx)):
        assert result.state is StepState.NEEDS_HUMAN
    assert fake.posts() == []


async def test_detail_names_storage_and_the_project() -> None:
    result = await _step(ManagedNeon("vercel")).inspect(_ctx(FakeEnv()))
    assert "Storage" in result.detail
    assert "kadoomi" in result.detail
    assert "DATABASE_URL" in result.detail


async def test_organization_not_managed_by_vercel_still_creates_the_project() -> None:
    fake = ManagedNeon("")
    env = FakeEnv()
    result = await _step(fake).apply(_ctx(env))
    assert result.state is StepState.DONE
    assert len(fake.posts()) == 1
    assert env.values["DATABASE_URL"] == _URI


@pytest.mark.parametrize("managed_by", ["vercel", ""])
async def test_database_url_in_vercel_skips_the_step(managed_by: str) -> None:
    fake = ManagedNeon(managed_by)
    step, ctx = _step(fake), _ctx(FakeEnv({"DATABASE_URL": "set"}))
    for result in (await step.inspect(ctx), await step.apply(ctx)):
        assert result.state is StepState.SKIPPED
    assert fake.posts() == []


async def test_unreadable_organization_list_keeps_the_previous_behaviour() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/organizations"):
            return httpx.Response(403, json={"message": "forbidden"})
        return httpx.Response(200, json={"projects": []})

    client = NeonClient(_KEY, httpx.MockTransport(refuse), "org_a")
    assert await client.managed_by_vercel() is False


async def test_creation_refused_elsewhere_stays_a_failure_with_neon_message() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(404, json={"message": "project creation not allowed"})
        if request.url.path.endswith("/organizations"):
            return httpx.Response(200, json={"organizations": [{"id": "org_a"}]})
        return httpx.Response(200, json={"projects": []})

    step = DatabaseStep(NeonClient(_KEY, httpx.MockTransport(refuse)), SecretRegistry())
    with pytest.raises(ServiceError) as erreur:
        await step.apply(_ctx(FakeEnv()))
    assert "project creation not allowed" in str(erreur.value)
