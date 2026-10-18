"""The Vercel steps — ADR-053, ticket-466. A fake API behind MockTransport, no network."""
import json
import logging

import httpx
import pytest

from tessera.services.provisioning import (
    DnsRecord,
    OnlineConfig,
    ProvisioningContext,
    ProvisioningPlan,
    ServiceError,
    StepState,
    VercelClient,
    VercelEnvWriter,
    VercelProjectStep,
    VercelRedeployStep,
    VercelVariablesStep,
)
from tessera.services.provisioning.vercel_dns import records_from_config
from tessera.utils.secrets import SecretRegistry

_TOKEN = "vtok_Q8w2ZkLmN4xPr7"
_VARIABLES = ["NEXT_PUBLIC_APP_URL", "SESSION_SECRET", "CRON_SECRET"]
_TXT = {"type": "TXT", "domain": "_vercel.example.com", "value": "vc-domain-verify=abc"}


class FakeVercel:
    """A minimal Vercel: state in attributes, every request recorded."""

    def __init__(self, project: bool = False, domain: bool = False, envs: tuple[str, ...] = (),
                 verified: bool = False, deployed: bool = True,
                 www: bool | None = None) -> None:
        self.project, self.domain, self.verified = project, domain, verified
        self.envs, self.deployed = list(envs), deployed
        # Sans précision, www suit le domaine : il est là quand le domaine l'est.
        self.www = domain if www is None else www
        self.requests: list[httpx.Request] = []

    def calls(self, method: str, prefix: str) -> list[httpx.Request]:
        return [r for r in self.requests
                if r.method == method and r.url.path.startswith(prefix)]

    def body(self, request: httpx.Request) -> dict[str, object]:
        loaded: dict[str, object] = json.loads(request.content)
        return loaded

    def _absent(self) -> httpx.Response:
        return httpx.Response(404, json={"error": {"code": "not_found", "message": "gone"}})

    def _domain_payload(self) -> dict[str, object]:
        return {"name": "example.com", "verified": self.verified,
                "verification": [] if self.verified else [_TXT]}

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        key, path = request.method, request.url.path
        if key == "GET" and path == "/v9/projects/demo":
            return httpx.Response(200, json={"id": "prj_1"}) if self.project else self._absent()
        if key == "POST" and path == "/v11/projects":
            self.project = True
            return httpx.Response(200, json={"id": "prj_1"})
        return self._route_domains_and_env(request)

    def _route_domains_and_env(self, request: httpx.Request) -> httpx.Response:
        key, path = request.method, request.url.path
        if path == "/v9/projects/demo/domains/example.com":
            return httpx.Response(200, json=self._domain_payload()) if self.domain else self._absent()
        if key == "POST" and path == "/v10/projects/demo/domains":
            if self.body(request)["name"] == "www.example.com":
                self.www = True
                return httpx.Response(200, json={"name": "www.example.com", "verified": True})
            self.domain = True
            return httpx.Response(200, json=self._domain_payload())
        if path == "/v9/projects/demo/domains/www.example.com":
            return httpx.Response(200, json={"verified": True}) if self.www else self._absent()
        if path == "/v6/domains/www.example.com/config":
            return httpx.Response(200, json={
                "misconfigured": not self.verified,
                "recommendedCNAME": [{"rank": 1, "value": "cname.vercel-dns.com."}]})
        if path == "/v6/domains/example.com/config":
            return httpx.Response(200, json={
                "misconfigured": not self.verified,
                "recommendedIPv4": [{"rank": 2, "value": ["1.1.1.1"]},
                                    {"rank": 1, "value": ["76.76.21.21"]}],
                "recommendedCNAME": [{"rank": 1, "value": "cname.vercel-dns.com."}]})
        return self._route_env_and_deployments(request)

    def _route_env_and_deployments(self, request: httpx.Request) -> httpx.Response:
        key, path = request.method, request.url.path
        if key == "GET" and path == "/v10/projects/demo/env":
            return httpx.Response(200, json={"envs": [{"key": k} for k in self.envs]})
        if key == "POST" and path == "/v10/projects/demo/env":
            self.envs.append(str(self.body(request)["key"]))
            return httpx.Response(200, json={})
        if key == "GET" and path == "/v6/deployments":
            found = [{"uid": "dpl_1", "state": "READY"}] if self.deployed else []
            return httpx.Response(200, json={"deployments": found})
        if key == "POST" and path == "/v13/deployments":
            return httpx.Response(200, json={})
        return httpx.Response(500, json={"error": {"code": "unexpected_route"}})


def _client(fake: FakeVercel, token: str = _TOKEN, team: str = "") -> VercelClient:
    return VercelClient(token, team, httpx.MockTransport(fake))


def _ctx(client: VercelClient, domain: str = "example.com",
         remote: str | None = "owner/demo") -> ProvisioningContext:
    online = OnlineConfig(domain=domain, resources=["vercel"])
    return ProvisioningContext("demo", online, VercelEnvWriter(client, "demo"), github_remote=remote)


def _steps(client: VercelClient) -> list[VercelProjectStep | VercelVariablesStep | VercelRedeployStep]:
    return [VercelProjectStep(client), VercelVariablesStep(client, SecretRegistry()),
            VercelRedeployStep(client)]


# ------------------------------------------------------------------
# Project
# ------------------------------------------------------------------


async def test_existing_project_is_not_recreated() -> None:
    fake = FakeVercel(project=True, domain=True, verified=True)
    client = _client(fake)
    step = VercelProjectStep(client)
    assert (await step.inspect(_ctx(client))).state is StepState.SKIPPED
    await step.apply(_ctx(client))
    assert fake.calls("POST", "/v11/projects") == []


async def test_missing_project_is_created_with_the_github_remote() -> None:
    fake = FakeVercel()
    client = _client(fake)
    step = VercelProjectStep(client)
    assert (await step.inspect(_ctx(client))).state is StepState.TODO
    assert fake.calls("POST", "/v11/projects") == []
    await step.apply(_ctx(client))
    corps = fake.body(fake.calls("POST", "/v11/projects")[0])
    assert corps == {"name": "demo", "gitRepository": {"type": "github", "repo": "owner/demo"}}


async def test_repo_not_found_asks_to_install_the_vercel_github_app() -> None:
    fake = FakeVercel()
    base = fake.__call__

    def refuse(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/v11/projects":
            return httpx.Response(400, json={"error": {"code": "repo_not_found"}})
        return base(request)

    client = VercelClient(_TOKEN, "", httpx.MockTransport(refuse))
    result = await VercelProjectStep(client).apply(_ctx(client))
    assert result.state is StepState.NEEDS_HUMAN
    assert "github.com/apps/vercel" in result.detail
    assert "owner/demo" in result.detail
    assert fake.calls("POST", "/v10/projects/demo/domains") == []


async def test_other_project_creation_errors_still_raise() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(403, json={"error": {"code": "forbidden"}})
        return httpx.Response(404, json={"error": {"code": "not_found"}})

    client = VercelClient(_TOKEN, "", httpx.MockTransport(refuse))
    with pytest.raises(ServiceError):
        await VercelProjectStep(client).apply(_ctx(client))


async def test_project_without_remote_is_created_unlinked() -> None:
    fake = FakeVercel()
    client = _client(fake)
    await VercelProjectStep(client).apply(_ctx(client, remote=None))
    assert fake.body(fake.calls("POST", "/v11/projects")[0]) == {"name": "demo"}


# ------------------------------------------------------------------
# Domain and DNS
# ------------------------------------------------------------------


async def test_missing_domain_is_added_and_dns_records_are_requested() -> None:
    fake = FakeVercel(project=True)
    client = _client(fake)
    ctx = _ctx(client)
    result = await VercelProjectStep(client).apply(ctx)
    assert result.state is StepState.DONE
    assert fake.body(fake.calls("POST", "/v10/projects/demo/domains")[0]) == {"name": "example.com"}
    assert ctx.wanted_dns == [
        DnsRecord("TXT", "_vercel.example.com", "vc-domain-verify=abc"),
        DnsRecord("A", "example.com", "76.76.21.21"),
        DnsRecord("CNAME", "www.example.com", "cname.vercel-dns.com"),
    ]


async def test_dns_records_are_not_requested_twice() -> None:
    fake = FakeVercel(project=True, domain=True)
    client = _client(fake)
    ctx = _ctx(client)
    await VercelProjectStep(client).inspect(ctx)
    await VercelProjectStep(client).inspect(ctx)
    assert ctx.wanted_dns.count(DnsRecord("A", "example.com", "76.76.21.21")) == 1
    assert ctx.wanted_dns.count(DnsRecord("CNAME", "www.example.com", "cname.vercel-dns.com")) == 1
    assert len(ctx.wanted_dns) == 3


def test_subdomain_asks_for_a_cname_and_apex_for_an_a_record() -> None:
    config: dict[str, object] = {
        "recommendedIPv4": [{"rank": 1, "value": ["76.76.21.21"]}],
        "recommendedCNAME": [{"rank": 1, "value": "cname.vercel-dns.com."}],
    }
    assert records_from_config("app.example.com", config) == [
        DnsRecord("CNAME", "app.example.com", "cname.vercel-dns.com")
    ]
    assert records_from_config("example.com", config) == [
        DnsRecord("A", "example.com", "76.76.21.21")
    ]
    assert records_from_config("example.com", {}) == []


async def test_verified_domain_asks_for_no_dns_record() -> None:
    fake = FakeVercel(project=True, domain=True, verified=True)
    client = _client(fake)
    ctx = _ctx(client)
    await VercelProjectStep(client).apply(ctx)
    assert ctx.wanted_dns == []
    assert fake.calls("POST", "/v10/projects/demo/domains") == []


# ------------------------------------------------------------------
# Variables
# ------------------------------------------------------------------


async def test_absent_variables_are_written_sensitive_except_the_public_one() -> None:
    fake = FakeVercel(project=True)
    client = _client(fake)
    ctx = _ctx(client)
    result = await VercelVariablesStep(client, SecretRegistry()).apply(ctx)
    assert result.state is StepState.DONE
    ecrites = {str(fake.body(r)["key"]): fake.body(r) for r in fake.calls("POST", "/v10/projects/demo/env")}
    assert set(ecrites) == set(_VARIABLES)
    assert ecrites["NEXT_PUBLIC_APP_URL"]["type"] == "plain"
    assert ecrites["NEXT_PUBLIC_APP_URL"]["value"] == "https://example.com"
    for nom in ("SESSION_SECRET", "CRON_SECRET"):
        assert ecrites[nom]["type"] == "sensitive"
        assert len(str(ecrites[nom]["value"])) >= 32
    assert ecrites["SESSION_SECRET"]["value"] != ecrites["CRON_SECRET"]["value"]
    assert ctx.changed_env == set(_VARIABLES)


async def test_existing_variable_is_never_rewritten() -> None:
    fake = FakeVercel(project=True, envs=("SESSION_SECRET",))
    client = _client(fake)
    ctx = _ctx(client)
    await VercelVariablesStep(client, SecretRegistry()).apply(ctx)
    ecrites = [fake.body(r)["key"] for r in fake.calls("POST", "/v10/projects/demo/env")]
    assert sorted(str(k) for k in ecrites) == ["CRON_SECRET", "NEXT_PUBLIC_APP_URL"]
    assert ctx.changed_env == {"CRON_SECRET", "NEXT_PUBLIC_APP_URL"}


async def test_env_writer_leaves_an_existing_variable_untouched() -> None:
    fake = FakeVercel(project=True, envs=("SESSION_SECRET",))
    writer = VercelEnvWriter(_client(fake), "demo")
    await writer.set_env("SESSION_SECRET", "other-value")
    assert fake.calls("POST", "/v10/projects/demo/env") == []
    assert await writer.has_env("SESSION_SECRET") and not await writer.has_env("CRON_SECRET")


async def test_variables_inspect_names_what_is_missing_without_writing() -> None:
    fake = FakeVercel(project=True, envs=("SESSION_SECRET",))
    client = _client(fake)
    result = await VercelVariablesStep(client, SecretRegistry()).inspect(_ctx(client))
    assert result.state is StepState.TODO
    assert "CRON_SECRET" in result.detail and "SESSION_SECRET" not in result.detail
    assert fake.calls("POST", "/") == []


# ------------------------------------------------------------------
# Redeploy, through the plan
# ------------------------------------------------------------------


async def test_redeploy_runs_only_when_a_variable_was_written_during_the_run() -> None:
    fake = FakeVercel()
    client = _client(fake)
    plan = ProvisioningPlan(_steps(client), secrets=SecretRegistry())
    first = await plan.run(_ctx(client))
    assert [o.result.state for o in first] == [StepState.DONE] * 3
    redeploys = fake.calls("POST", "/v13/deployments")
    assert len(redeploys) == 1
    assert fake.body(redeploys[0]) == {"name": "demo", "deploymentId": "dpl_1", "target": "production"}
    fake.requests.clear()
    second = await plan.run(_ctx(client))
    assert second[-1].result.state is StepState.SKIPPED
    assert fake.calls("POST", "/v13/deployments") == []
    assert fake.calls("POST", "/v10/projects/demo/env") == []


async def test_redeploy_is_skipped_when_nothing_was_written() -> None:
    fake = FakeVercel(project=True)
    client = _client(fake)
    step = VercelRedeployStep(client)
    assert (await step.inspect(_ctx(client))).state is StepState.SKIPPED
    assert [r.method for r in fake.requests] == ["GET", "GET"]


# ------------------------------------------------------------------
# No token, no leak
# ------------------------------------------------------------------


@pytest.mark.parametrize("token", ["", "   "])
async def test_without_token_every_step_needs_a_human_and_sends_nothing(token: str) -> None:
    fake = FakeVercel()
    client = _client(fake, token=token)
    ctx = _ctx(client)
    ctx.changed_env.add("SESSION_SECRET")
    for step in _steps(client):
        assert (await step.inspect(ctx)).state is StepState.NEEDS_HUMAN
        assert (await step.apply(ctx)).state is StepState.NEEDS_HUMAN
    assert fake.requests == []


async def test_team_id_is_sent_and_the_token_is_a_bearer_header() -> None:
    fake = FakeVercel()
    client = _client(fake, team="team_42")
    await client.get_project("demo")
    assert fake.requests[0].url.params["teamId"] == "team_42"
    assert fake.requests[0].headers["Authorization"] == f"Bearer {_TOKEN}"


async def test_service_error_carries_neither_token_nor_value() -> None:
    echo = f"rejected {_TOKEN} and value s3cr3t-value"

    def refuse(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"error": {"code": "forbidden", "message": echo}})

    client = VercelClient(_TOKEN, transport=httpx.MockTransport(refuse))
    with pytest.raises(ServiceError) as erreur:
        await client.create_env("demo", "SESSION_SECRET", "s3cr3t-value", True)
    texte = str(erreur.value) + repr(erreur.value.args)
    assert "HTTP 403" in texte and "forbidden" in texte
    assert _TOKEN not in texte and "s3cr3t-value" not in texte


async def test_network_failure_becomes_a_service_error_without_detail() -> None:
    def broken(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(f"cannot reach {request.url} with {_TOKEN}")

    client = VercelClient(_TOKEN, transport=httpx.MockTransport(broken))
    with pytest.raises(ServiceError) as erreur:
        await client.get_project("demo")
    assert erreur.value.code == "unreachable" and _TOKEN not in str(erreur.value)


async def test_logs_and_results_never_hold_the_token_or_a_written_value(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    fake = FakeVercel()
    client = _client(fake, team="team_42")
    plan = ProvisioningPlan(_steps(client), secrets=SecretRegistry())
    sorties = await plan.run(_ctx(client))
    valeurs = [str(fake.body(r)["value"]) for r in fake.calls("POST", "/v10/projects/demo/env")]
    assert len(valeurs) == 3
    # Les enregistrements bruts, avant tout masque du formateur.
    vus = [str(r.__dict__) + r.getMessage() for r in caplog.records]
    vus += [o.result.detail for o in sorties]
    for secret in [_TOKEN, *valeurs[1:]]:
        assert not any(secret in texte for texte in vus)
