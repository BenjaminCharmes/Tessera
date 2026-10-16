"""The database step — ADR-053, ticket-467. A fake Neon behind MockTransport, no network."""
import json
import logging

import httpx
import pytest

from tessera.services.pipeline_events import OrchestratorEvent
from tessera.services.provisioning import (
    DatabaseStep,
    NeonClient,
    OnlineConfig,
    ProvisioningContext,
    ProvisioningPlan,
    ServiceError,
    StepState,
)
from tessera.utils.secrets import SecretRegistry

_KEY = "napi_Zk4Lm8Qw2Xr7Vb"
_PASSWORD = "p4ss-Wq9Zt3Lm"
_URI = f"postgresql://owner:{_PASSWORD}@ep-demo.neon.tech/neondb?sslmode=require"


class FakeNeon:
    """A minimal Neon: projects by name, every request recorded."""

    def __init__(self, projects: tuple[str, ...] = (), uri_on_create: bool = True) -> None:
        self.projects = {f"prj_{i}": name for i, name in enumerate(projects)}
        self.uri_on_create = uri_on_create
        self.requests: list[httpx.Request] = []

    def calls(self, method: str, path: str) -> list[httpx.Request]:
        return [r for r in self.requests if r.method == method and r.url.path.endswith(path)]

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path.removeprefix("/api/v2")
        if request.method == "GET" and path == "/projects":
            needle = request.url.params["search"]
            found = [{"id": i, "name": n} for i, n in self.projects.items() if needle in n]
            return httpx.Response(200, json={"projects": found})
        if request.method == "POST" and path == "/projects":
            name = json.loads(request.content)["project"]["name"]
            self.projects["prj_new"] = name
            uris = [{"connection_uri": _URI}] if self.uri_on_create else []
            return httpx.Response(201, json={"project": {"id": "prj_new"}, "connection_uris": uris})
        return self._route_project(request, path)

    def _route_project(self, request: httpx.Request, path: str) -> httpx.Response:
        if path.endswith("/branches"):
            return httpx.Response(200, json={"branches": [
                {"id": "br_side", "default": False}, {"id": "br_main", "default": True}]})
        if path.endswith("/databases"):
            return httpx.Response(200, json={"databases": [{"name": "neondb", "owner_name": "owner"}]})
        if path.endswith("/connection_uri"):
            return httpx.Response(200, json={"uri": _URI})
        return httpx.Response(500, json={"error": {"code": "unexpected_route"}})


class FakeEnv:
    """The Vercel side: what is written, and optionally a failure that echoes the value."""

    def __init__(self, present: tuple[str, ...] = (), fail_echoing: bool = False) -> None:
        self.values: dict[str, str] = {name: "hidden" for name in present}
        self.writes: list[str] = []
        self.fail_echoing = fail_echoing

    async def has_env(self, name: str) -> bool:
        return name in self.values

    async def set_env(self, name: str, value: str) -> None:
        if self.fail_echoing:
            body = json.dumps({"error": {"code": "bad_request", "message": f"rejected {value}"}})
            raise ServiceError.from_response("vercel", 400, body)
        self.values[name] = value
        self.writes.append(name)


def _client(fake: FakeNeon, key: str = _KEY) -> NeonClient:
    return NeonClient(key, httpx.MockTransport(fake))


def _ctx(env: FakeEnv) -> ProvisioningContext:
    return ProvisioningContext("demo", OnlineConfig(domain="example.com"), env)


def _step(client: NeonClient) -> DatabaseStep:
    return DatabaseStep(client, SecretRegistry())


async def test_existing_project_is_not_recreated_and_its_uri_is_written() -> None:
    fake, env = FakeNeon(("demo",)), FakeEnv()
    ctx = _ctx(env)
    result = await _step(_client(fake)).apply(ctx)
    assert result.state is StepState.DONE
    assert fake.calls("POST", "/projects") == []
    assert env.values == {"DATABASE_URL": _URI}
    assert ctx.changed_env == {"DATABASE_URL"}
    query = fake.calls("GET", "/connection_uri")[0].url.params
    assert (query["branch_id"], query["database_name"], query["role_name"]) == (
        "br_main", "neondb", "owner")


async def test_missing_project_is_created_and_its_uri_is_written() -> None:
    fake, env = FakeNeon(), FakeEnv()
    result = await _step(_client(fake)).apply(_ctx(env))
    assert result.state is StepState.DONE
    creations = fake.calls("POST", "/projects")
    assert [json.loads(r.content) for r in creations] == [{"project": {"name": "demo"}}]
    assert env.values == {"DATABASE_URL": _URI}


async def test_uri_is_read_by_the_api_when_creation_does_not_return_it() -> None:
    fake, env = FakeNeon(uri_on_create=False), FakeEnv()
    await _step(_client(fake)).apply(_ctx(env))
    assert len(fake.calls("GET", "/connection_uri")) == 1
    assert env.values == {"DATABASE_URL": _URI}


async def test_name_is_matched_exactly_not_as_a_substring() -> None:
    fake, env = FakeNeon(("demo-staging",)), FakeEnv()
    await _step(_client(fake)).apply(_ctx(env))
    assert len(fake.calls("POST", "/projects")) == 1


async def test_variable_already_in_vercel_skips_without_any_neon_request() -> None:
    fake, env = FakeNeon(), FakeEnv(present=("DATABASE_URL",))
    step = _step(_client(fake))
    assert (await step.inspect(_ctx(env))).state is StepState.SKIPPED
    assert (await step.apply(_ctx(env))).state is StepState.SKIPPED
    assert fake.requests == [] and env.writes == []


async def test_inspect_reads_without_creating_or_writing() -> None:
    fake, env = FakeNeon(), FakeEnv()
    result = await _step(_client(fake)).inspect(_ctx(env))
    assert result.state is StepState.TODO
    assert fake.calls("POST", "/projects") == [] and fake.calls("GET", "/connection_uri") == []
    assert env.writes == []


async def test_two_projects_with_the_same_name_fail_without_creation() -> None:
    fake, env = FakeNeon(("demo", "demo")), FakeEnv()
    step = _step(_client(fake))
    assert (await step.inspect(_ctx(env))).state is StepState.FAILED
    assert (await step.apply(_ctx(env))).state is StepState.FAILED
    assert fake.calls("POST", "/projects") == [] and env.writes == []


async def test_without_key_the_step_is_manual_when_the_variable_exists() -> None:
    fake, env = FakeNeon(), FakeEnv(present=("DATABASE_URL",))
    result = await _step(_client(fake, key="  ")).inspect(_ctx(env))
    assert result.state is StepState.MANUAL
    assert fake.requests == []


async def test_without_key_the_step_needs_a_human_with_the_instruction() -> None:
    fake, env = FakeNeon(), FakeEnv()
    step = _step(_client(fake, key=""))
    for result in (await step.inspect(_ctx(env)), await step.apply(_ctx(env))):
        assert result.state is StepState.NEEDS_HUMAN
        assert "NEON_API_KEY" in result.detail and "DATABASE_URL" in result.detail
    assert fake.requests == [] and env.writes == []


async def test_service_error_does_not_repeat_the_uri_from_a_response_body() -> None:
    echo = f"cannot use {_URI} with {_PASSWORD}"

    def refuse(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"code": "invalid", "message": echo})

    client = NeonClient(_KEY, httpx.MockTransport(refuse))
    with pytest.raises(ServiceError) as erreur:
        await client.connection_uri("prj_0")
    texte = str(erreur.value) + repr(erreur.value.args)
    assert "HTTP 422" in texte and _PASSWORD not in texte and _KEY not in texte


async def test_network_failure_becomes_a_service_error_without_detail() -> None:
    def broken(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(f"cannot reach {request.url} with {_KEY}")

    with pytest.raises(ServiceError) as erreur:
        await NeonClient(_KEY, httpx.MockTransport(broken)).find_projects("demo")
    assert erreur.value.code == "unreachable" and _KEY not in str(erreur.value)


async def test_uri_appears_in_no_log_event_result_or_failure(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    events: list[OrchestratorEvent] = []

    async def emit(event: OrchestratorEvent) -> None:
        events.append(event)

    registry = SecretRegistry()
    for env in (FakeEnv(), FakeEnv(fail_echoing=True)):
        plan = ProvisioningPlan([DatabaseStep(_client(FakeNeon()), registry)], emit, registry)
        outcomes = await plan.run(_ctx(env))
        assert outcomes[0].result.state in (StepState.DONE, StepState.FAILED)
        assert "***" not in outcomes[0].result.detail
    seen = [str(r.__dict__) + r.getMessage() for r in caplog.records]
    seen += [str(e) for e in events]
    assert len(events) == 2
    for secret in (_URI, _PASSWORD, _KEY):
        assert not any(secret in text for text in seen)
    assert {_URI, _PASSWORD} <= registry.valeurs()
