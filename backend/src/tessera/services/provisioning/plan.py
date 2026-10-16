"""The ordered run of provisioning steps — ADR-053, ticket-465."""
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Optional

from tessera.services.pipeline_events import EventCallback, EventType, OrchestratorEvent
from tessera.services.provisioning.errors import ServiceError
from tessera.services.provisioning.steps import (
    STOPPING_STATES,
    ProvisioningContext,
    ProvisioningStep,
    StepResult,
    StepState,
)
from tessera.utils.logger import get_logger
from tessera.utils.secrets import SECRETS, SecretRegistry

_logger = get_logger(__name__)

#: What ``inspect`` can say that leaves nothing for ``apply`` to do.
_SANS_APPLY: frozenset[StepState] = frozenset(
    {StepState.SKIPPED, StepState.MANUAL, StepState.NEEDS_HUMAN, StepState.FAILED}
)


@dataclass(frozen=True)
class StepOutcome:
    """The final result of one step of a run."""

    step: str
    result: StepResult


class ProvisioningPlan:
    """Runs the steps in their declared order, reading the world first."""

    def __init__(
        self,
        steps: Sequence[ProvisioningStep],
        emit: Optional[EventCallback] = None,
        secrets: SecretRegistry = SECRETS,
    ) -> None:
        self._steps = list(steps)
        self._emit = emit
        self._secrets = secrets

    async def run(self, ctx: ProvisioningContext, dry_run: bool = False) -> list[StepOutcome]:
        """Inspect then apply each step; stop after ``failed`` or ``needs_human``.

        ``dry_run`` never calls ``apply``: what is missing is reported ``todo``.
        What an earlier step did stays done — nothing is undone.
        """
        sorties: list[StepOutcome] = []
        for step in self._steps:
            resultat = self._masquer(await self._run_step(step, ctx, dry_run))
            sorties.append(StepOutcome(step.name, resultat))
            await self._publish(ctx, step.name, resultat)
            if resultat.state in STOPPING_STATES:
                break
        return sorties

    async def _run_step(
        self, step: ProvisioningStep, ctx: ProvisioningContext, dry_run: bool
    ) -> StepResult:
        lu = await self._guarded(step, step.inspect, ctx)
        if lu.state in _SANS_APPLY:
            return lu
        if dry_run:
            return StepResult(StepState.TODO, lu.detail)
        return await self._guarded(step, step.apply, ctx)

    def _masquer(self, resultat: StepResult) -> StepResult:
        # Le détail ne doit jamais porter un secret ; si une étape se trompe,
        # le masque tient la ligne avant qu'il sorte du plan.
        return StepResult(resultat.state, self._secrets.mask(resultat.detail))

    async def _guarded(
        self,
        step: ProvisioningStep,
        action: Callable[[ProvisioningContext], Awaitable[StepResult]],
        ctx: ProvisioningContext,
    ) -> StepResult:
        """Call one step action, turning any failure into a ``failed`` result."""
        try:
            resultat = await action(ctx)
        except ServiceError as erreur:
            return StepResult(StepState.FAILED, str(erreur))
        except Exception as erreur:
            # Le message d'une exception inconnue peut répéter un secret :
            # seul son type sort.
            _logger.error(
                "provisioning_step_crashed",
                extra={"step": step.name, "error": type(erreur).__name__},
            )
            return StepResult(StepState.FAILED, f"unexpected {type(erreur).__name__}")
        return resultat

    async def _publish(self, ctx: ProvisioningContext, nom: str, resultat: StepResult) -> None:
        if self._emit is None:
            return
        await self._emit(
            OrchestratorEvent(
                type=EventType.PROVISIONING_STEP,
                ticket_id="",
                project_id=ctx.project_id,
                data={
                    "step": nom,
                    "state": str(resultat.state),
                    "detail": resultat.detail,
                },
            )
        )
