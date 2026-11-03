"""The Vercel deployment step — ticket-489. A fake Vercel behind MockTransport, no network."""
import json
from typing import Optional

import httpx
import pytest

from tessera.config import settings
from tessera.services.provisioning import (
    OnlineConfig,
    ProvisioningContext,
    ServiceError,
    StepState,
    VercelClient,
    VercelEnvWriter,
    VercelRedeployStep,
)
from tessera.services.provisioning.github_repo import GitHubRepoLookup
from tessera.services.provisioning.vercel_deployments import VercelDeployment, deployment_from

_TOKEN = "vtok_Q8w2ZkLmN4xPr7"
_GH_TOKEN = "ghp_Z3kPq9Lm2Xw7Rt5"
_BUILD_LOG = "npm ERR! secret-build-log-line"


class FakeVercel:
    """A Vercel project with a configurable newest production deployment."""

    def __init__(self, listed: Optional[dict[str, object]] = None,
                 created: Optional[dict[str, object]] = None, project: bool = True) -> None:
        self.listed, self.created, self.project = listed, created or {}, project
        self.requests: list[httpx.Request] = []

    def posts(self) -> list[httpx.Request]:
        return [r for r in self.requests if r.method == "POST"]

    def body(self, request: httpx.Request) -> dict[str, object]:
        loaded: dict[str, object] = json.loads(request.content)
        return loaded

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        key, path = request.method, request.url.path
        if key == "GET" and path == "/v9/projects/demo":
            if not self.project:
                return httpx.Response(404, json={"error": {"code": "not_found"}})
            return httpx.Response(200, json={"id": "prj_1"})
        if key == "GET" and path == "/v6/deployments":
            found = [self.listed] if self.listed is not None else []
            return httpx.Response(200, json={"deployments": found})
        if key == "POST" and path == "/v13/deployments":
            return httpx.Response(200, json=self.created)
        return httpx.Response(500, json={"error": {"code": "unexpected_route"}})


class FakeRepos:
    """A repository id source that remembers what it was asked."""

    def __init__(self, repo_id: Optional[int] = 4242) -> None:
        self.repo_id_value = repo_id
        self.asked: list[str] = []

    async def repo_id(self, repo: str) -> Optional[int]:
        self.asked.append(repo)
        return self.repo_id_value


def _step(fake: FakeVercel, repos: Optional[FakeRepos] = None) -> VercelRedeployStep:
    client = VercelClient(_TOKEN, "", httpx.MockTransport(fake))
    return VercelRedeployStep(client, repos or FakeRepos())


def _ctx(remote: Optional[str] = "owner/demo", base: str = "") -> ProvisioningContext:
    online = OnlineConfig(domain="example.com", resources=["vercel"])
    writer = VercelEnvWriter(VercelClient(_TOKEN), "demo")
    return ProvisioningContext("demo", online, writer, github_remote=remote, base_branch=base)


def _ready() -> dict[str, object]:
    return {"uid": "dpl_1", "state": "READY"}


# ------------------------------------------------------------------
# First deployment
# ------------------------------------------------------------------


async def test_project_without_production_deployment_gets_one_from_the_base_branch() -> None:
    fake = FakeVercel(created={"id": "dpl_9", "readyState": "QUEUED"})
    step = _step(fake)
    ctx = _ctx(base="main")
    assert (await step.inspect(ctx)).state is StepState.TODO
    assert fake.posts() == []
    result = await step.apply(ctx)
    assert result.state is StepState.PENDING
    envoi = fake.posts()[0]
    assert envoi.url.params["skipAutoDetectionConfirmation"] == "1"
    assert fake.body(envoi) == {
        "name": "demo",
        "target": "production",
        "gitSource": {"type": "github", "repoId": 4242, "ref": "main"},
    }


async def test_first_deployment_falls_back_to_the_configured_base_branch() -> None:
    fake = FakeVercel()
    await _step(fake).apply(_ctx())
    source = fake.body(fake.posts()[0])["gitSource"]
    assert isinstance(source, dict) and source["ref"] == settings.github_base_branch


async def test_first_deployment_without_a_pending_state_reply_is_pending() -> None:
    fake = FakeVercel(created={})
    assert (await _step(fake).apply(_ctx())).state is StepState.PENDING


async def test_first_deployment_ready_at_once_is_done() -> None:
    fake = FakeVercel(created={"id": "dpl_9", "readyState": "READY"})
    assert (await _step(fake).apply(_ctx())).state is StepState.DONE


async def test_canceled_deployment_does_not_count_as_a_deployment() -> None:
    fake = FakeVercel(listed={"uid": "dpl_0", "state": "CANCELED"})
    step = _step(fake)
    assert (await step.inspect(_ctx())).state is StepState.TODO
    await step.apply(_ctx())
    assert len(fake.posts()) == 1


async def test_missing_vercel_project_is_reported_by_inspect_and_failed_by_apply() -> None:
    fake = FakeVercel(project=False)
    step = _step(fake)
    assert (await step.inspect(_ctx())).state is StepState.TODO
    assert (await step.apply(_ctx())).state is StepState.FAILED
    assert fake.posts() == []


# ------------------------------------------------------------------
# Where the repository id comes from
# ------------------------------------------------------------------


async def test_repository_id_is_read_for_the_github_remote() -> None:
    repos = FakeRepos(repo_id=777)
    fake = FakeVercel()
    await _step(fake, repos).apply(_ctx(remote="octo/widget"))
    assert repos.asked == ["octo/widget"]
    source = fake.body(fake.posts()[0])["gitSource"]
    assert isinstance(source, dict) and source["repoId"] == 777


async def test_lookup_reads_the_id_of_owner_repo_from_the_github_api() -> None:
    vus: list[httpx.Request] = []

    def github(request: httpx.Request) -> httpx.Response:
        vus.append(request)
        return httpx.Response(200, json={"id": 98765, "name": "demo"})

    lookup = GitHubRepoLookup(_GH_TOKEN, httpx.MockTransport(github))
    assert await lookup.repo_id("owner/demo") == 98765
    assert vus[0].url.host == "api.github.com" and vus[0].url.path == "/repos/owner/demo"
    assert vus[0].headers["Authorization"] == f"Bearer {_GH_TOKEN}"


async def test_lookup_without_token_sends_no_authorization_header() -> None:
    vus: list[httpx.Request] = []

    def github(request: httpx.Request) -> httpx.Response:
        vus.append(request)
        return httpx.Response(200, json={"id": 5})

    assert await GitHubRepoLookup("", httpx.MockTransport(github)).repo_id("owner/demo") == 5
    assert "Authorization" not in vus[0].headers


@pytest.mark.parametrize("slug", ["", "demo", "../etc/passwd", "a/b/c", "owner/de mo"])
async def test_lookup_refuses_a_malformed_slug_without_a_request(slug: str) -> None:
    def github(request: httpx.Request) -> httpx.Response:
        raise AssertionError("no request expected")

    assert await GitHubRepoLookup("", httpx.MockTransport(github)).repo_id(slug) is None


async def test_lookup_returns_none_on_404_and_raises_a_clean_error_otherwise() -> None:
    def absent(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"message": "Not Found"})

    def broken(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"message": f"oops {_GH_TOKEN}"})

    assert await GitHubRepoLookup(_GH_TOKEN, httpx.MockTransport(absent)).repo_id("o/r") is None
    with pytest.raises(ServiceError) as erreur:
        await GitHubRepoLookup(_GH_TOKEN, httpx.MockTransport(broken)).repo_id("o/r")
    assert "HTTP 500" in str(erreur.value) and _GH_TOKEN not in str(erreur.value)


async def test_no_github_remote_needs_a_human_and_creates_nothing() -> None:
    fake = FakeVercel()
    result = await _step(fake).apply(_ctx(remote=None))
    assert result.state is StepState.NEEDS_HUMAN
    assert fake.posts() == []


async def test_unreadable_repository_needs_a_human_and_creates_nothing() -> None:
    fake = FakeVercel()
    result = await _step(fake, FakeRepos(repo_id=None)).apply(_ctx())
    assert result.state is StepState.NEEDS_HUMAN
    assert "owner/demo" in result.detail and fake.posts() == []


# ------------------------------------------------------------------
# A project that is already deployed
# ------------------------------------------------------------------


async def test_deployed_project_without_changed_variable_stays_skipped() -> None:
    fake = FakeVercel(listed=_ready())
    step = _step(fake)
    assert (await step.inspect(_ctx())).state is StepState.SKIPPED
    assert (await step.apply(_ctx())).state is StepState.SKIPPED
    assert fake.posts() == []


async def test_deployed_project_with_a_changed_variable_is_redeployed() -> None:
    fake = FakeVercel(listed=_ready())
    step = _step(fake)
    ctx = _ctx()
    ctx.changed_env.add("SESSION_SECRET")
    assert (await step.inspect(ctx)).state is StepState.TODO
    assert (await step.apply(ctx)).state is StepState.DONE
    assert fake.body(fake.posts()[0]) == {
        "name": "demo", "deploymentId": "dpl_1", "target": "production"}


async def test_building_deployment_is_pending_and_nothing_is_created() -> None:
    fake = FakeVercel(listed={"uid": "dpl_1", "state": "BUILDING"})
    step = _step(fake)
    assert (await step.inspect(_ctx())).state is StepState.PENDING
    assert (await step.apply(_ctx())).state is StepState.PENDING
    assert fake.posts() == []


# ------------------------------------------------------------------
# A deployment in ERROR
# ------------------------------------------------------------------


async def test_listed_deployment_in_error_fails_with_vercels_error_code() -> None:
    fake = FakeVercel(listed={"uid": "dpl_1", "state": "ERROR", "errorCode": "BUILD_FAILED",
                              "errorMessage": _BUILD_LOG})
    result = await _step(fake).inspect(_ctx())
    assert result.state is StepState.FAILED
    assert "BUILD_FAILED" in result.detail and _BUILD_LOG not in result.detail


async def test_created_deployment_in_error_fails_with_vercels_error_code() -> None:
    fake = FakeVercel(created={"id": "dpl_9", "readyState": "ERROR", "errorCode": "BUILD_FAILED",
                               "errorMessage": _BUILD_LOG})
    result = await _step(fake).apply(_ctx())
    assert result.state is StepState.FAILED
    assert "BUILD_FAILED" in result.detail and _BUILD_LOG not in result.detail


async def test_error_without_a_usable_code_says_unknown() -> None:
    fake = FakeVercel(listed={"uid": "dpl_1", "state": "ERROR", "errorCode": "not a code!"})
    result = await _step(fake).inspect(_ctx())
    assert result.state is StepState.FAILED and "unknown" in result.detail


# ------------------------------------------------------------------
# Reading a deployment
# ------------------------------------------------------------------


def test_deployment_is_read_from_a_list_entry_or_a_creation_reply() -> None:
    assert deployment_from({"uid": "a", "state": "ready"}) == VercelDeployment("a", "READY")
    assert deployment_from({"id": "b", "readyState": "ERROR", "errorCode": "x"}) == VercelDeployment(
        "b", "ERROR", "x")
    assert deployment_from({"state": "READY"}) is None
    assert deployment_from(None) is None


def test_deployment_state_flags() -> None:
    assert VercelDeployment("a", "BUILDING").in_progress
    assert VercelDeployment("a", "ERROR").failed
    assert VercelDeployment("a", "CANCELED").canceled
    assert VercelDeployment("a", "READY").ready
    assert not VercelDeployment("a", "").in_progress


async def test_without_token_the_step_needs_a_human_and_sends_nothing() -> None:
    fake = FakeVercel()
    step = VercelRedeployStep(VercelClient("", "", httpx.MockTransport(fake)), FakeRepos())
    assert (await step.inspect(_ctx())).state is StepState.NEEDS_HUMAN
    assert (await step.apply(_ctx())).state is StepState.NEEDS_HUMAN
    assert fake.requests == []
