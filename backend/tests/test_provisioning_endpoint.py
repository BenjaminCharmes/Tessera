"""The provisioning endpoint — ADR-053, ticket-471. Fake steps, no service."""
import json
from collections.abc import Iterator, Sequence
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from tessera.config import settings
from tessera.main import app
from tessera.services.event_hub import EVENT_HUB, Abonnement
from tessera.services.pipeline_events import EventType, OrchestratorEvent
from tessera.services.provisioning import (
    OnlineConfig,
    ProvisioningContext,
    ProvisioningStep,
    ServiceError,
    StepResult,
    StepState,
)
from tessera.services.provisioning.launcher import (
    PROVISIONING_LOCK,
    ProvisioningSetup,
    build_setup,
    get_setup_factory,
)
from tessera.utils.secrets import SECRETS

_URL = "/api/v1/projects/mon-projet/provision"
_SECRET = "sk_live_Zk3fQ9aLmN27xPw"
_TOKEN = "s3cret-de-test"


class _NoEnv:
    async def has_env(self, name: str) -> bool:
        return False

    async def set_env(self, name: str, value: str) -> None:
        return None


class _Step:
    """A scripted step that writes what it was asked to do in a journal."""

    def __init__(
        self,
        name: str,
        journal: list[str],
        inspected: StepState = StepState.TODO,
        crash: Exception | None = None,
    ) -> None:
        self.name = name
        self._journal = journal
        self._inspected = inspected
        self._crash = crash

    async def inspect(self, ctx: ProvisioningContext) -> StepResult:
        self._journal.append(f"inspect:{self.name}")
        return StepResult(self._inspected, f"{self.name} read")

    async def apply(self, ctx: ProvisioningContext) -> StepResult:
        self._journal.append(f"apply:{self.name}")
        if self._crash is not None:
            raise self._crash
        return StepResult(StepState.DONE, f"{self.name} done")


def _override(steps: Sequence[ProvisioningStep]) -> None:
    def _factory(
        project_id: str, online: OnlineConfig, remote: str | None
    ) -> ProvisioningSetup:
        context = ProvisioningContext(project_id, online, _NoEnv(), remote)
        return ProvisioningSetup(list(steps), context)

    app.dependency_overrides[get_setup_factory] = lambda: _factory


def _write_agents(project: Path, online: object) -> None:
    (project / "agents.json").write_text(json.dumps({"online": online}), encoding="utf-8")


@pytest.fixture(autouse=True)
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    ws = tmp_path / "workspace"
    project = ws / "mon-projet"
    project.mkdir(parents=True)
    (project / "CLAUDE.md").write_text("# mon-projet\n", encoding="utf-8")
    _write_agents(project, {"domain": "example.com", "resources": ["vercel"]})
    monkeypatch.setattr(settings, "ide_workspace_dir", ws)
    monkeypatch.setattr(settings, "static_token", "")
    PROVISIONING_LOCK.release("mon-projet")
    yield ws
    app.dependency_overrides.pop(get_setup_factory, None)
    PROVISIONING_LOCK.release("mon-projet")
    SECRETS.clear()


@pytest.fixture
def events() -> Iterator[Abonnement]:
    abonnement = EVENT_HUB.subscribe()
    yield abonnement
    EVENT_HUB.retirer(abonnement)


def _client() -> TestClient:
    return TestClient(app)


def _states(events: list[OrchestratorEvent]) -> list[tuple[str, str]]:
    return [(str(e.data["step"]), str(e.data["state"])) for e in events]


# ------------------------------------------------------------------
# POST: start, refusals
# ------------------------------------------------------------------


def test_post_returns_202_and_runs_the_plan(events: Abonnement) -> None:
    journal: list[str] = []
    _override([_Step("a", journal), _Step("b", journal)])

    resp = _client().post(_URL)

    assert resp.status_code == 202
    assert resp.json() == {"project_id": "mon-projet", "steps": ["a", "b"]}
    assert journal == ["inspect:a", "apply:a", "inspect:b", "apply:b"]
    assert _states(events.vider()) == [("a", "done"), ("b", "done")]


def test_post_publishes_provisioning_step_events(events: Abonnement) -> None:
    _override([_Step("a", [])])

    _client().post(_URL)

    (event,) = events.vider()
    assert event.type is EventType.PROVISIONING_STEP
    assert event.project_id == "mon-projet"


def test_post_unknown_project_is_404() -> None:
    _override([])
    assert _client().post("/api/v1/projects/jamais-vu/provision").status_code == 404


def test_post_without_online_block_is_422(workspace: Path) -> None:
    (workspace / "mon-projet" / "agents.json").write_text("{}", encoding="utf-8")
    journal: list[str] = []
    _override([_Step("a", journal)])

    resp = _client().post(_URL)

    assert resp.status_code == 422
    assert journal == []
    assert not PROVISIONING_LOCK.is_running("mon-projet")


def test_post_with_invalid_online_block_names_the_field(workspace: Path) -> None:
    _write_agents(workspace / "mon-projet", {"domain": "pas un domaine", "resources": []})
    _override([])

    resp = _client().post(_URL)

    assert resp.status_code == 422
    assert "online.domain" in resp.json()["detail"]


# ------------------------------------------------------------------
# POST: lock
# ------------------------------------------------------------------


def test_second_post_during_a_provisioning_is_409() -> None:
    journal: list[str] = []
    _override([_Step("a", journal)])
    assert PROVISIONING_LOCK.try_acquire("mon-projet")

    resp = _client().post(_URL)

    assert resp.status_code == 409
    assert journal == []
    # Le refus ne libère pas le verrou de la mise en ligne en cours.
    assert PROVISIONING_LOCK.is_running("mon-projet")


def test_lock_is_released_after_a_successful_run() -> None:
    _override([_Step("a", [])])

    assert _client().post(_URL).status_code == 202
    assert not PROVISIONING_LOCK.is_running("mon-projet")


def test_lock_is_released_after_a_step_failure() -> None:
    _override([_Step("a", [], crash=ServiceError("vercel", 500, "boom"))])

    assert _client().post(_URL).status_code == 202
    assert not PROVISIONING_LOCK.is_running("mon-projet")
    assert _client().post(_URL).status_code == 202


def test_lock_is_released_when_the_events_cannot_be_published(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _broken(event: OrchestratorEvent) -> None:
        raise RuntimeError("hub down")

    monkeypatch.setattr(EVENT_HUB, "publish", _broken)
    _override([_Step("a", [])])

    assert _client().post(_URL).status_code == 202
    assert not PROVISIONING_LOCK.is_running("mon-projet")


def test_setup_failure_is_500_without_detail_and_frees_the_lock() -> None:
    def _factory(project_id: str, online: OnlineConfig, remote: str | None) -> ProvisioningSetup:
        raise RuntimeError(f"cannot build with {_SECRET}")

    app.dependency_overrides[get_setup_factory] = lambda: _factory

    resp = _client().post(_URL)

    assert resp.status_code == 500
    assert _SECRET not in resp.text
    assert not PROVISIONING_LOCK.is_running("mon-projet")


# ------------------------------------------------------------------
# GET: read only
# ------------------------------------------------------------------


def test_get_only_inspects_and_returns_the_state_per_step(events: Abonnement) -> None:
    journal: list[str] = []
    _override([_Step("a", journal), _Step("b", journal, StepState.SKIPPED)])

    resp = _client().get(_URL)

    assert resp.status_code == 200
    assert resp.json() == [
        {"step": "a", "state": "todo", "detail": "a read"},
        {"step": "b", "state": "skipped", "detail": "b read"},
    ]
    assert journal == ["inspect:a", "inspect:b"]
    assert events.vider() == []
    assert not PROVISIONING_LOCK.is_running("mon-projet")


def test_get_is_allowed_while_a_provisioning_runs() -> None:
    _override([_Step("a", [])])
    assert PROVISIONING_LOCK.try_acquire("mon-projet")

    assert _client().get(_URL).status_code == 200


def test_get_unknown_project_is_404_and_without_online_block_is_422(workspace: Path) -> None:
    _override([])
    assert _client().get("/api/v1/projects/jamais-vu/provision").status_code == 404
    (workspace / "mon-projet" / "agents.json").write_text("{}", encoding="utf-8")
    assert _client().get(_URL).status_code == 422


def test_get_without_tokens_reads_the_world_with_the_real_steps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for champ in ("vercel_token", "neon_api_key", "cloudflare_api_token"):
        monkeypatch.setattr(settings, champ, SecretStr(""))

    resp = _client().get(_URL)

    assert resp.status_code == 200
    (etape,) = resp.json()
    assert (etape["step"], etape["state"]) == ("vercel_project", "needs_human")


# ------------------------------------------------------------------
# Failure: an event, never a trace or a token
# ------------------------------------------------------------------


def test_step_exception_becomes_a_failed_event_without_trace_or_token(
    events: Abonnement,
) -> None:
    SECRETS.register(_SECRET)
    boom = RuntimeError(f"upstream said {_SECRET}")
    _override([_Step("a", [], crash=boom), _Step("b", [])])

    post = _client().post(_URL)
    emitted = events.vider()
    get = _client().get(_URL)

    assert _states(emitted) == [("a", "failed")]
    assert emitted[0].data["detail"] == "unexpected RuntimeError"
    for texte in (post.text, get.text, json.dumps([e.data for e in emitted])):
        assert _SECRET not in texte
        assert "Traceback" not in texte


def test_get_reports_a_crashing_step_as_failed_without_leaking() -> None:
    SECRETS.register(_SECRET)

    class _Crashing(_Step):
        async def inspect(self, ctx: ProvisioningContext) -> StepResult:
            raise RuntimeError(f"upstream said {_SECRET}")

    _override([_Crashing("a", [])])

    resp = _client().get(_URL)

    assert resp.status_code == 200
    assert resp.json() == [{"step": "a", "state": "failed", "detail": "unexpected RuntimeError"}]
    assert _SECRET not in resp.text


# ------------------------------------------------------------------
# STATIC_TOKEN
# ------------------------------------------------------------------


def test_both_routes_require_the_bearer_token_when_static_token_is_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "static_token", _TOKEN)
    journal: list[str] = []
    _override([_Step("a", journal)])
    entetes = {"Authorization": f"Bearer {_TOKEN}"}

    assert _client().post(_URL).status_code == 401
    assert _client().get(_URL).status_code == 401
    assert journal == []
    assert _client().post(_URL, headers={"Authorization": "Bearer faux"}).status_code == 401
    assert _client().get(_URL, headers=entetes).status_code == 200
    assert _client().post(_URL, headers=entetes).status_code == 202


# ------------------------------------------------------------------
# The plan built from online.resources
# ------------------------------------------------------------------


def _names(resources: list[str]) -> list[str]:
    bloc: dict[str, object] = {"domain": "example.com", "resources": resources}
    if "stripe" in resources:
        bloc["stripe"] = {"webhook_path": "/api/stripe", "events": ["checkout.session.completed"]}
    online = OnlineConfig.model_validate(bloc)
    return [step.name for step in build_setup("mon-projet", online, "me/repo").steps]


def test_plan_with_resend_and_stripe_follows_the_declared_order() -> None:
    assert _names(["vercel", "database", "resend", "dns", "stripe"]) == [
        "vercel_project",
        "database",
        "variables",
        "resend_domain",
        "stripe",
        "dns",
        "resend_verify",
        "redeploy",
        "health_check",
    ]


def test_plan_without_resend_nor_stripe_has_neither_step() -> None:
    noms = _names(["vercel", "database", "dns"])
    assert not any(nom.startswith("resend") or nom == "stripe" for nom in noms)


def test_plan_follows_the_dependency_order() -> None:
    assert _names(["vercel", "database", "dns"]) == [
        "vercel_project",
        "database",
        "variables",
        "dns",
        "redeploy",
        "health_check",
    ]


def test_plan_without_vercel_keeps_only_what_is_listed() -> None:
    assert _names([]) == ["dns"]
    assert _names(["database"]) == ["database", "dns"]


def test_setup_carries_the_remote_of_the_project() -> None:
    online = OnlineConfig(domain="example.com", resources=[])
    setup = build_setup("mon-projet", online, "me/repo")
    assert setup.context.github_remote == "me/repo"
    assert setup.context.project_id == "mon-projet"
