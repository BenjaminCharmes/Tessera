"""State shared by the stages of one pipeline run — ticket-046.

`run_pipeline` used to carry this as local variables threaded through 490
inline lines. Naming it makes explicit what each stage may read and what it
hands to the next, and gives the per-round reset a single place to live.
"""
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from tessera.models.ticket import Ticket, TicketStatus
from tessera.services.dialogue import DialogueChannel
from tessera.services.pipeline_events import (
    EventCallback,
    EventType,
    OrchestratorEvent,
)
from tessera.utils.logger import get_logger

if TYPE_CHECKING:
    from tessera.services.orchestrator import Orchestrator

_logger = get_logger(__name__)


@dataclass
class PipelineRun:
    """Everything a stage needs to read, or to hand to the next one.

    The per-round fields are cleared by `start_round`: they describe the
    current attempt, not the run as a whole. Forgetting that reset is how a
    second round would review the first round's diff.
    """

    project_id: str
    ticket: Ticket
    on_event: EventCallback
    run_id: str | None = None

    branch: str | None = None
    review_feedback: list[str] = field(default_factory=list)

    # Le dialogue avec l'utilisateur pendant le run (ticket-066). Par défaut
    # non interactif : un run lancé sans canal branché — un test, un appel
    # programmatique — ne doit jamais se suspendre en attendant une réponse
    # que personne ne viendra donner.
    dialogue: DialogueChannel = field(
        default_factory=lambda: DialogueChannel(interactive=False)
    )

    # La conversation du codeur, reprise d'un tour à l'autre (ticket-187).
    # Elle appartient au run — donc à la branche — et jamais au ticket : un
    # nouveau run repart à vide. Un provider qui n'en rend pas la laisse à
    # None, et chaque tour reste l'appel complet.
    session_codeur: str | None = None

    # La liste des fichiers suivis, calculée une fois avant le premier agent
    # (ticket-190) : le codeur ne doit pas y voir ses propres fichiers du
    # tour précédent. Vide quand git n'a rien à dire.
    carte_du_depot: str = ""
    #: Le plan rendu avant le premier tour, si le ticket en demande un
    #: (ticket-243). Vide : pas de plan, ou un plan qui a échoué.
    plan: str = ""

    # Instantané de memory/ et tickets/ pris avant le premier agent, utilisé
    # pour calculer le diff d'artefacts à la fin de chaque tour (ticket-274).
    # None quand aucun chemin de projet n'est configuré.
    artifact_snapshot: dict[str, str] | None = None

    # --- remis à zéro à chaque tour ---
    round_num: int = 0
    reviewed_code: str = ""
    test_result: Any = None
    test_context: str = ""
    security_context: str = ""
    # Ce que le tour ajoute au contexte projet — retours du reviewer,
    # consignes de l'utilisateur. C'est tout ce qu'un codeur qui reprend sa
    # session a besoin de recevoir : le reste, il l'a déjà (ticket-187).
    contexte_du_tour: str = ""
    # Diff textuel entre l'instantané et l'état courant de memory/ et tickets/.
    # Transmis au reviewer et au validateur uniquement — jamais à l'audit
    # sécurité (code uniquement) et jamais dans un commit (ticket-274).
    artifact_diff: str = ""

    @property
    def stop_requested(self) -> bool:
        """True dès que l'utilisateur a demandé l'arrêt de ce run."""
        return self.dialogue.stop_requested

    @property
    def ticket_id(self) -> str:
        return self.ticket.id

    def start_round(self, round_num: int) -> None:
        self.round_num = round_num
        self.reviewed_code = ""
        self.test_result = None
        self.test_context = ""
        self.security_context = ""
        self.contexte_du_tour = ""
        self.artifact_diff = ""


async def emit(run: PipelineRun, event_type: EventType, **data: Any) -> None:
    """Emit a ticket-scoped event with `data` built from keyword arguments."""
    await run.on_event(
        OrchestratorEvent(type=event_type, ticket_id=run.ticket_id, data=dict(data))
    )


async def set_status(
    orch: "Orchestrator", run: PipelineRun, status: TicketStatus
) -> None:
    """Move the ticket to `status` and announce it — always both.

    The folder carries the status and the UI listens to the event: updating
    one without the other makes the board disagree with the filesystem.
    """
    await orch._ticket_svc.update_status(run.ticket_id, status)
    await emit(run, EventType.TICKET_STATUS_CHANGED, status=status.value)


_MARQUE_TOLERANT = "_tessera_tolerant"


def tolerant(on_event: EventCallback) -> EventCallback:
    """Wrap `on_event` so that an emitter failure is logged, never raised.

    L'émetteur est le plus souvent une socket vers l'onglet de l'IDE. Fermer
    cet onglet en plein tour faisait remonter l'erreur dans le run, qui
    s'arrêtait **avant** son commit : arbre sale, file bloquée (ADR-018). En
    mode single le routeur avalait déjà l'erreur, pas en mode file ni
    autonome. Le garde vit ici pour que les trois modes — et le chat — le
    tiennent sans dépendre de ce que chaque appelant a pensé à faire
    (ticket-121).

    Une vraie coroutine plutôt qu'un objet appelable : les appelants
    existants la reconnaissent avec `inspect.iscoroutinefunction`.
    """
    if getattr(on_event, _MARQUE_TOLERANT, False):
        return on_event

    async def envoyer(event: OrchestratorEvent) -> None:
        try:
            await on_event(event)
        except Exception as exc:  # noqa: BLE001 — l'émetteur ne tue jamais le run
            _logger.warning(
                "event_emit_failed",
                extra={"event": event.type.value, "error": str(exc)},
            )

    setattr(envoyer, _MARQUE_TOLERANT, True)
    return envoyer
