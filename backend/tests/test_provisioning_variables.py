"""Variables declared per project (generate / derive) — ADR-053, ticket-483."""
import logging

import pytest

from tessera.services.provisioning import (
    OnlineConfig,
    ProvisioningContext,
    ProvisioningPlan,
    StepState,
    VercelEnvWriter,
    VercelVariablesStep,
)
from tessera.services.provisioning.online_config import OnlineConfigError, parse_online_config
from tessera.utils.secrets import SecretRegistry
from tests.test_provisioning_vercel import FakeVercel, _client


def _written(fake: FakeVercel) -> dict[str, str]:
    """Name -> value of every variable the fake received."""
    return {
        str(fake.body(r)["key"]): str(fake.body(r)["value"])
        for r in fake.calls("POST", "/v10/projects/demo/env")
    }


def _ctx_for(fake: FakeVercel, **declared: object) -> tuple[ProvisioningContext, VercelVariablesStep]:
    client = _client(fake)
    online = OnlineConfig.model_validate(
        {"domain": "kadoomi.com", "resources": ["vercel"], **declared}
    )
    ctx = ProvisioningContext("demo", online, VercelEnvWriter(client, "demo"))
    return ctx, VercelVariablesStep(client, SecretRegistry())


async def test_generate_replaces_the_default_secrets() -> None:
    fake = FakeVercel(project=True)
    ctx, step = _ctx_for(fake, generate=["BETTER_AUTH_SECRET"])
    await step.apply(ctx)
    ecrites = _written(fake)
    assert set(ecrites) == {"NEXT_PUBLIC_APP_URL", "BETTER_AUTH_SECRET"}
    assert "SESSION_SECRET" not in ecrites and len(ecrites["BETTER_AUTH_SECRET"]) >= 32


async def test_derive_computes_the_value_from_the_declared_domain() -> None:
    fake = FakeVercel(project=True)
    ctx, step = _ctx_for(fake, derive={"BETTER_AUTH_URL": "https://{domain}"})
    await step.apply(ctx)
    ecrites = _written(fake)
    assert ecrites["BETTER_AUTH_URL"] == "https://kadoomi.com"
    assert {"SESSION_SECRET", "CRON_SECRET"} <= set(ecrites)
    assert "BETTER_AUTH_URL" in ctx.changed_env


async def test_variables_already_in_vercel_are_not_rewritten() -> None:
    fake = FakeVercel(project=True, envs=("BETTER_AUTH_SECRET", "BETTER_AUTH_URL"))
    ctx, step = _ctx_for(
        fake,
        generate=["BETTER_AUTH_SECRET"],
        derive={"BETTER_AUTH_URL": "https://{domain}"},
    )
    result = await step.apply(ctx)
    assert set(_written(fake)) == {"NEXT_PUBLIC_APP_URL"}
    assert "BETTER_AUTH" not in result.detail


async def test_without_generate_the_default_stays_session_and_cron() -> None:
    fake = FakeVercel(project=True)
    ctx, step = _ctx_for(fake)
    await step.apply(ctx)
    assert set(_written(fake)) == {"NEXT_PUBLIC_APP_URL", "SESSION_SECRET", "CRON_SECRET"}


async def test_an_empty_generate_list_generates_nothing() -> None:
    fake = FakeVercel(project=True)
    ctx, step = _ctx_for(fake, generate=[])
    await step.apply(ctx)
    assert set(_written(fake)) == {"NEXT_PUBLIC_APP_URL"}


async def test_inspect_names_declared_variables_that_are_missing() -> None:
    fake = FakeVercel(project=True, envs=("NEXT_PUBLIC_APP_URL",))
    ctx, step = _ctx_for(
        fake, generate=["BETTER_AUTH_SECRET"], derive={"BETTER_AUTH_URL": "https://{domain}"}
    )
    result = await step.inspect(ctx)
    assert result.state is StepState.TODO
    assert "BETTER_AUTH_SECRET" in result.detail and "BETTER_AUTH_URL" in result.detail
    assert fake.calls("POST", "/") == []


async def test_a_generated_value_appears_in_no_log_and_no_step_detail(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    fake = FakeVercel(project=True)
    ctx, step = _ctx_for(fake, generate=["BETTER_AUTH_SECRET"])
    plan = ProvisioningPlan([step], secrets=SecretRegistry())
    sorties = await plan.run(ctx)
    secret = _written(fake)["BETTER_AUTH_SECRET"]
    vus = [str(r.__dict__) + r.getMessage() for r in caplog.records]
    vus += [o.result.detail for o in sorties]
    assert not any(secret in texte for texte in vus)


async def test_resend_resource_writes_the_sender_address_from_the_project_name() -> None:
    fake = FakeVercel(project=True)
    ctx, step = _ctx_for(fake, domain="example.com", resources=["vercel", "resend"])
    ctx.project_name = "Mon Projet"
    result = await step.apply(ctx)
    assert _written(fake)["RESEND_FROM_EMAIL"] == "Mon Projet <bonjour@example.com>"
    assert "RESEND_FROM_EMAIL" in ctx.changed_env
    assert "RESEND_FROM_EMAIL" in result.detail


async def test_sender_address_falls_back_on_the_project_id_without_a_name() -> None:
    fake = FakeVercel(project=True)
    ctx, step = _ctx_for(fake, domain="example.com", resources=["vercel", "resend"])
    await step.apply(ctx)
    assert _written(fake)["RESEND_FROM_EMAIL"] == "demo <bonjour@example.com>"


async def test_a_derived_sender_address_wins_over_the_default() -> None:
    fake = FakeVercel(project=True)
    ctx, step = _ctx_for(
        fake,
        domain="example.com",
        resources=["vercel", "resend"],
        derive={"RESEND_FROM_EMAIL": "Equipe <contact@{domain}>"},
    )
    ctx.project_name = "Mon Projet"
    await step.apply(ctx)
    ecrites = [r for r in fake.calls("POST", "/v10/projects/demo/env")
               if fake.body(r)["key"] == "RESEND_FROM_EMAIL"]
    assert len(ecrites) == 1
    assert _written(fake)["RESEND_FROM_EMAIL"] == "Equipe <contact@example.com>"


async def test_a_sender_address_already_in_vercel_is_not_rewritten() -> None:
    fake = FakeVercel(project=True, envs=("RESEND_FROM_EMAIL",))
    ctx, step = _ctx_for(fake, resources=["vercel", "resend"])
    result = await step.apply(ctx)
    assert "RESEND_FROM_EMAIL" not in _written(fake)
    assert "RESEND_FROM_EMAIL" not in result.detail
    assert "RESEND_FROM_EMAIL" not in ctx.changed_env


async def test_without_the_resend_resource_no_sender_address_is_written() -> None:
    fake = FakeVercel(project=True)
    ctx, step = _ctx_for(fake)
    await step.apply(ctx)
    assert "RESEND_FROM_EMAIL" not in _written(fake)


async def test_inspect_lists_the_sender_address_among_the_missing_variables() -> None:
    fake = FakeVercel(project=True, envs=("NEXT_PUBLIC_APP_URL", "SESSION_SECRET", "CRON_SECRET"))
    ctx, step = _ctx_for(fake, resources=["vercel", "resend"])
    result = await step.inspect(ctx)
    assert result.state is StepState.TODO
    assert result.detail == "missing: RESEND_FROM_EMAIL"
    assert fake.calls("POST", "/") == []


def test_a_variable_name_must_look_like_an_environment_variable() -> None:
    with pytest.raises(OnlineConfigError, match="online.generate"):
        parse_online_config({"domain": "kadoomi.com", "generate": ["not a name"]})
    with pytest.raises(OnlineConfigError, match="online.derive"):
        parse_online_config({"domain": "kadoomi.com", "derive": {"bad-name": "x"}})
