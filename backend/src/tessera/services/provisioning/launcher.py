"""What the provisioning endpoint needs to start a run — ADR-053, ticket-471.

Only the explicit request of the user reaches this module: it is imported by
``routers/provisioning.py`` and by nothing in the pipeline, the chat or the
agents. The lock is its own, distinct from ``RunLock``: a project can be put
online while a pipeline run works on its code, and the other way round.
"""
from collections.abc import Callable
from dataclasses import dataclass
from typing import Optional

from tessera.config import settings
from tessera.services.event_hub import EVENT_HUB
from tessera.services.pipeline_events import EventType, OrchestratorEvent
from tessera.services.provisioning.cloudflare import CloudflareClient
from tessera.services.provisioning.cloudflare_steps import DnsStep
from tessera.services.provisioning.neon import NeonClient
from tessera.services.provisioning.neon_steps import DatabaseStep
from tessera.services.provisioning.online_config import OnlineConfig
from tessera.services.provisioning.plan import ProvisioningPlan
from tessera.services.provisioning.resend import ResendClient
from tessera.services.provisioning.resend_steps import ResendDomainStep, ResendVerifyStep
from tessera.services.provisioning.steps import ProvisioningContext, ProvisioningStep
from tessera.services.provisioning.stripe_client import StripeClient
from tessera.services.provisioning.stripe_step import StripeStep
from tessera.services.provisioning.vercel import VercelClient, VercelEnvWriter
from tessera.services.provisioning.vercel_steps import (
    VercelProjectStep,
    VercelRedeployStep,
    VercelVariablesStep,
)
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

#: Nom d'étape de l'événement qui rend compte d'un échec hors de toute étape.
RUN_STEP_NAME = "provisioning"


class ProvisioningLock:
    """One online provisioning at a time per project.

    Like ``RunLock`` it fails loudly instead of queuing: a second click must
    learn that the first is still running. In the memory of the process.
    """

    def __init__(self) -> None:
        self._busy: set[str] = set()

    def try_acquire(self, project_id: str) -> bool:
        """Take the project; ``False`` when a provisioning already holds it."""
        # Aucun `await` entre le test et l'ajout : la boucle ne s'intercale pas.
        if project_id in self._busy:
            return False
        self._busy.add(project_id)
        return True

    def release(self, project_id: str) -> None:
        """Free the project; releasing a free project is harmless."""
        self._busy.discard(project_id)

    def is_running(self, project_id: str) -> bool:
        """Tell whether a provisioning of the project is under way."""
        return project_id in self._busy


PROVISIONING_LOCK = ProvisioningLock()


@dataclass
class ProvisioningSetup:
    """The steps of one run and the context they share."""

    steps: list[ProvisioningStep]
    context: ProvisioningContext


SetupFactory = Callable[[str, OnlineConfig, Optional[str]], ProvisioningSetup]


def _build_steps(online: OnlineConfig, vercel: VercelClient) -> list[ProvisioningStep]:
    steps: list[ProvisioningStep] = []
    if online.wants("vercel"):
        steps.append(VercelProjectStep(vercel))
    if online.wants("database"):
        steps.append(DatabaseStep(NeonClient.from_settings(settings)))
    if online.wants("vercel"):
        steps.append(VercelVariablesStep(vercel))
    resend = ResendClient.from_settings(settings) if online.wants("resend") else None
    if resend is not None:
        steps.append(ResendDomainStep(resend))
    if online.wants("stripe"):
        steps.append(StripeStep(StripeClient.from_settings(settings)))
    steps.append(DnsStep(CloudflareClient.from_settings(settings)))
    if resend is not None:
        steps.append(ResendVerifyStep(resend))
    if online.wants("vercel"):
        steps.append(VercelRedeployStep(vercel))
    return steps


def build_setup(
    project_id: str, online: OnlineConfig, github_remote: Optional[str]
) -> ProvisioningSetup:
    """Build the ordered steps from ``online.resources`` and the Tessera tokens.

    The order is the dependency order: the Vercel project first (the variables
    live in it), then the database that writes ``DATABASE_URL`` there, then the
    app variables, then the Resend domain and Stripe (both ask for records or
    write variables), then DNS — after every step that asks for a record — the
    Resend verification once the records exist, and the redeploy last, once
    every variable of the run is written.
    """
    vercel = VercelClient.from_settings(settings)
    steps = _build_steps(online, vercel)
    context = ProvisioningContext(
        project_id=project_id,
        online=online,
        env_writer=VercelEnvWriter(vercel, project_id),
        github_remote=github_remote,
    )
    return ProvisioningSetup(steps, context)


def get_setup_factory() -> SetupFactory:
    """FastAPI dependency: the factory the routes build their run with."""
    return build_setup


async def _publish_failure(project_id: str, erreur: Exception) -> None:
    event = OrchestratorEvent(
        type=EventType.PROVISIONING_STEP,
        ticket_id="",
        project_id=project_id,
        # Seul le type de l'exception sort : son message peut citer un secret.
        data={
            "step": RUN_STEP_NAME,
            "state": "failed",
            "detail": f"unexpected {type(erreur).__name__}",
        },
    )
    try:
        await EVENT_HUB.publish(event)
    except Exception as echec:
        _logger.error("provisioning_failure_not_published", extra={"error": type(echec).__name__})


async def run_provisioning(setup: ProvisioningSetup) -> None:
    """Run the plan, one event per step, and always free the project's lock.

    A step that raises is already a ``failed`` event (the plan guards it); the
    ``except`` below only covers what happens around the steps.
    """
    project_id = setup.context.project_id
    try:
        plan = ProvisioningPlan(setup.steps, emit=EVENT_HUB.publish)
        await plan.run(setup.context)
    except Exception as erreur:
        _logger.error(
            "provisioning_run_crashed",
            extra={"project": project_id, "error": type(erreur).__name__},
        )
        await _publish_failure(project_id, erreur)
    finally:
        PROVISIONING_LOCK.release(project_id)
