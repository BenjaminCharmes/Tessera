"""The provisioning engine — ADR-053, ticket-465. Fake steps only, no service."""
import json
from pathlib import Path

import pytest

from tessera.services.pipeline_events import EventType, OrchestratorEvent
from tessera.services.provisioning import (
    OnlineConfig,
    OnlineConfigError,
    ProvisioningContext,
    ProvisioningPlan,
    ServiceError,
    StepResult,
    StepState,
    load_online_config,
)
from tessera.utils.secrets import SecretRegistry

_SECRET = "whsec_Zk3fQ9aLmN27xPw"


class _NoEnv:
    async def has_env(self, name: str) -> bool:
        return False

    async def set_env(self, name: str, value: str) -> None:
        return None


class _FakeStep:
    """A step whose inspect and apply answers are scripted."""

    def __init__(
        self,
        name: str,
        journal: list[str],
        inspected: StepResult,
        applied: StepResult | Exception | None = None,
    ) -> None:
        self.name = name
        self._journal = journal
        self._inspected = inspected
        self._applied = applied or StepResult(StepState.DONE, f"{name} created")

    async def inspect(self, ctx: ProvisioningContext) -> StepResult:
        self._journal.append(f"inspect:{self.name}")
        return self._inspected

    async def apply(self, ctx: ProvisioningContext) -> StepResult:
        self._journal.append(f"apply:{self.name}")
        if isinstance(self._applied, Exception):
            raise self._applied
        return self._applied


def _missing(detail: str = "missing") -> StepResult:
    return StepResult(StepState.TODO, detail)


def _ctx() -> ProvisioningContext:
    online = OnlineConfig(domain="example.com", resources=["vercel"])
    return ProvisioningContext("demo", online, _NoEnv())


class _Collector:
    def __init__(self) -> None:
        self.events: list[OrchestratorEvent] = []

    async def __call__(self, event: OrchestratorEvent) -> None:
        self.events.append(event)


# ------------------------------------------------------------------
# Order, stop, resume
# ------------------------------------------------------------------


async def test_steps_run_in_declared_order_each_inspected_then_applied() -> None:
    journal: list[str] = []
    steps = [_FakeStep(n, journal, _missing()) for n in ("a", "b", "c")]

    outcomes = await ProvisioningPlan(steps).run(_ctx())

    assert journal == ["inspect:a", "apply:a", "inspect:b", "apply:b", "inspect:c", "apply:c"]
    assert [o.step for o in outcomes] == ["a", "b", "c"]
    assert all(o.result.state is StepState.DONE for o in outcomes)


@pytest.mark.parametrize("stopping", [StepState.FAILED, StepState.NEEDS_HUMAN])
async def test_a_stopping_apply_halts_the_next_steps_and_keeps_the_previous(
    stopping: StepState,
) -> None:
    journal: list[str] = []
    steps = [
        _FakeStep("a", journal, _missing()),
        _FakeStep("b", journal, _missing(), StepResult(stopping, "stop")),
        _FakeStep("c", journal, _missing()),
    ]

    outcomes = await ProvisioningPlan(steps).run(_ctx())

    assert [o.step for o in outcomes] == ["a", "b"]
    assert outcomes[0].result.state is StepState.DONE
    assert outcomes[1].result.state is stopping
    assert "inspect:c" not in journal and "apply:c" not in journal


async def test_a_stopping_inspect_halts_without_applying_it() -> None:
    journal: list[str] = []
    steps = [
        _FakeStep("a", journal, StepResult(StepState.NEEDS_HUMAN, "token missing")),
        _FakeStep("b", journal, _missing()),
    ]

    outcomes = await ProvisioningPlan(steps).run(_ctx())

    assert journal == ["inspect:a"]
    assert [o.result.state for o in outcomes] == [StepState.NEEDS_HUMAN]


async def test_a_manual_step_does_not_stop_the_next_ones() -> None:
    journal: list[str] = []
    steps = [
        _FakeStep("a", journal, StepResult(StepState.MANUAL, "add the record")),
        _FakeStep("b", journal, _missing()),
    ]

    outcomes = await ProvisioningPlan(steps).run(_ctx())

    assert "apply:a" not in journal and "apply:b" in journal
    assert [o.result.state for o in outcomes] == [StepState.MANUAL, StepState.DONE]


async def test_a_complete_world_applies_nothing_and_emits_skipped_everywhere() -> None:
    journal: list[str] = []
    done = StepResult(StepState.SKIPPED, "already there")
    steps = [_FakeStep(n, journal, done) for n in ("a", "b")]
    collector = _Collector()

    await ProvisioningPlan(steps, collector).run(_ctx())

    assert not [line for line in journal if line.startswith("apply:")]
    assert [e.data["state"] for e in collector.events] == ["skipped", "skipped"]
    assert [e.data["step"] for e in collector.events] == ["a", "b"]


async def test_dry_run_never_applies_and_reports_todo_for_what_is_missing() -> None:
    journal: list[str] = []
    steps = [
        _FakeStep("a", journal, StepResult(StepState.SKIPPED, "there")),
        _FakeStep("b", journal, _missing("project absent")),
    ]

    outcomes = await ProvisioningPlan(steps).run(_ctx(), dry_run=True)

    assert not [line for line in journal if line.startswith("apply:")]
    assert [o.result.state for o in outcomes] == [StepState.SKIPPED, StepState.TODO]
    assert outcomes[1].result.detail == "project absent"


async def test_a_service_error_fails_the_step_with_status_and_code_only() -> None:
    journal: list[str] = []
    boom = ServiceError("vercel", 403, "forbidden")
    steps = [_FakeStep("a", journal, _missing(), boom), _FakeStep("b", journal, _missing())]

    outcomes = await ProvisioningPlan(steps).run(_ctx())

    assert outcomes[0].result == StepResult(StepState.FAILED, "vercel: HTTP 403 (forbidden)")
    assert len(outcomes) == 1


async def test_an_unexpected_exception_fails_without_its_message() -> None:
    journal: list[str] = []
    steps = [_FakeStep("a", journal, _missing(), RuntimeError(f"bad key {_SECRET}"))]

    outcomes = await ProvisioningPlan(steps).run(_ctx())

    assert outcomes[0].result.state is StepState.FAILED
    assert _SECRET not in outcomes[0].result.detail


# ------------------------------------------------------------------
# Secrets
# ------------------------------------------------------------------


async def test_no_provisioning_event_carries_a_registered_secret() -> None:
    registry = SecretRegistry()
    registry.register(_SECRET)
    journal: list[str] = []
    steps = [
        _FakeStep("a", journal, StepResult(StepState.SKIPPED, f"found {_SECRET}")),
        _FakeStep("b", journal, _missing(), StepResult(StepState.DONE, f"wrote {_SECRET}")),
    ]
    collector = _Collector()

    outcomes = await ProvisioningPlan(steps, collector, registry).run(_ctx())

    assert {e.type for e in collector.events} == {EventType.PROVISIONING_STEP}
    assert all(_SECRET not in e.model_dump_json() for e in collector.events)
    assert all(_SECRET not in o.result.detail for o in outcomes)
    assert collector.events[0].project_id == "demo"


def test_service_error_message_never_holds_the_response_body() -> None:
    body = json.dumps({"error": {"code": "invalid_key", "message": f"key {_SECRET} refused"}})

    erreur = ServiceError.from_response("stripe", 401, body)

    assert str(erreur) == "stripe: HTTP 401 (invalid_key)"
    assert _SECRET not in str(erreur) and _SECRET not in repr(erreur)
    assert _SECRET not in repr(erreur.args)


@pytest.mark.parametrize(
    "body",
    [
        json.dumps({"errors": [{"code": 1003, "message": _SECRET}]}),
        json.dumps({"name": "validation_error", "message": _SECRET}),
        json.dumps({"error": _SECRET}),
        json.dumps({"error": {"code": f"bad {_SECRET}"}}),
        f"not json {_SECRET}",
        b"\xff\xfe",
    ],
)
def test_service_error_reads_the_code_in_each_api_shape_and_never_the_rest(
    body: str | bytes,
) -> None:
    erreur = ServiceError.from_response("cloudflare", 400, body)

    assert _SECRET not in str(erreur)
    assert str(erreur).startswith("cloudflare: HTTP 400 (")


# ------------------------------------------------------------------
# The ``online`` block
# ------------------------------------------------------------------


def _write_agents(tmp_path: Path, data: object) -> Path:
    (tmp_path / "agents.json").write_text(json.dumps(data), encoding="utf-8")
    return tmp_path


def test_a_missing_online_block_gives_none(tmp_path: Path) -> None:
    assert load_online_config(tmp_path) is None
    assert load_online_config(_write_agents(tmp_path, {"services": []})) is None


def test_a_valid_online_block_is_read(tmp_path: Path) -> None:
    root = _write_agents(
        tmp_path,
        {
            "online": {
                "domain": "Example.FR",
                "resources": ["vercel", "stripe"],
                "stripe": {"webhook_path": "/api/hook", "events": ["checkout.session.completed"]},
            }
        },
    )

    config = load_online_config(root)

    assert config is not None
    assert config.domain == "example.fr"
    assert config.wants("stripe") and not config.wants("dns")
    assert config.stripe is not None and config.stripe.mode == "test"


@pytest.mark.parametrize(
    ("block", "field"),
    [
        ({"resources": ["vercel"]}, "online.domain"),
        ({"domain": "https://example.com", "resources": []}, "online.domain"),
        ({"domain": "example.com", "resources": ["vercel", "mailgun"]}, "online.resources.1"),
        ({"domain": "example.com", "resources": ["stripe"]}, "online.stripe"),
        (
            {"domain": "example.com", "stripe": {"webhook_path": "hook", "events": ["e"]}},
            "online.stripe.webhook_path",
        ),
        ({"domain": "example.com", "colour": "red"}, "online.colour"),
    ],
)
def test_an_invalid_online_block_is_refused_naming_the_field(
    tmp_path: Path, block: dict[str, object], field: str
) -> None:
    root = _write_agents(tmp_path, {"online": block})

    with pytest.raises(OnlineConfigError, match=field.replace(".", r"\.")):
        load_online_config(root)


def test_an_online_block_that_is_not_an_object_is_refused(tmp_path: Path) -> None:
    with pytest.raises(OnlineConfigError, match="online"):
        load_online_config(_write_agents(tmp_path, {"online": ["vercel"]}))
