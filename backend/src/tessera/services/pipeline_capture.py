"""Where the capture step sits in the pipeline — ticket-618.

Appelée une fois, sur un run approuvé, après la documentation et avant la
livraison. Elle ne s'ouvre que si le projet déclare `controle_visuel` et que le
diff approuvé touche un fichier d'interface ; sinon, aucun processus n'est créé.
"""
from typing import TYPE_CHECKING

from tessera.services.captures_session import lire_le_jeton
from tessera.services.controle_visuel import ControleVisuel, controle_du
from tessera.services.diff_changements import lire_diff
from tessera.services.etape_de_capture import ResultatCapture, prendre_les_captures
from tessera.services.git_workspace import GitWorkspaceError
from tessera.services.pipeline_events import (
    EventCallback,
    EventType,
    OrchestratorEvent,
    PipelineResult,
)
from tessera.utils.logger import get_logger

if TYPE_CHECKING:
    from tessera.services.orchestrator import Orchestrator

_logger = get_logger(__name__)


async def fichiers_du_diff(orch: "Orchestrator") -> list[str]:
    """The paths the approved branch changes since its fork point."""
    # getattr : les doubles d'espace de travail des tests n'ont pas cette méthode.
    lire = getattr(orch._git_workspace, "diff_depuis_base", None)
    if lire is None:
        return []
    try:
        diff = await lire()
    except GitWorkspaceError as exc:
        _logger.warning("diff_de_capture_illisible", extra={"erreur": str(exc)})
        return []
    return [fichier.chemin for fichier in lire_diff(diff)] if isinstance(diff, str) else []


def _ligne(ticket_id: str, resultat: ResultatCapture) -> str:
    durees = f"démarrage {resultat.demarrage_ms} ms, capture {resultat.capture_ms} ms"
    if resultat.cause is not None:
        return f"[{ticket_id}] captures: échec — {resultat.cause} ({durees})"
    return f"[{ticket_id}] captures: {len(resultat.images)} image(s) — {durees}"


async def _annoncer(
    orch: "Orchestrator", ticket_id: str, resultat: ResultatCapture, on_event: EventCallback
) -> None:
    orch._log(_ligne(ticket_id, resultat))
    await on_event(
        OrchestratorEvent(
            type=EventType.VISUAL_CHECK,
            ticket_id=ticket_id,
            data={
                "outcome": "failed" if resultat.cause is not None else "captured",
                "images": resultat.images,
                "startup_ms": resultat.demarrage_ms,
                "capture_ms": resultat.capture_ms,
                "reason": resultat.cause,
            },
        )
    )


def _jeton(orch: "Orchestrator") -> tuple[str | None, str | None]:
    """The session token and, when it is missing, the cause that says where to put it."""
    controle = orch._controle_visuel
    session = controle.captures.session if controle is not None else None
    if session is None or orch._depot is None:
        return None, None
    jeton = lire_le_jeton(orch._depot, session)
    if jeton is None:
        # Le message nomme la variable et le fichier, jamais une valeur.
        return None, (
            f"la variable `{session.jeton_env}` est absente ou vide dans "
            f"`{session.fichier_env}`"
        )
    return jeton, None


def _a_relire(controle: ControleVisuel, resultat: ResultatCapture) -> str | None:
    """Why the PR waits for a human: only the `relire` mode asks for it."""
    if controle.mode != "relire":
        return None
    if resultat.cause is not None:
        return f"captures échouées ({resultat.cause})"
    return f"{len(resultat.images)} capture(s) prise(s)"


async def _terminer(
    orch: "Orchestrator",
    controle: ControleVisuel,
    ticket_id: str,
    resultat: ResultatCapture,
    on_event: EventCallback,
) -> str | None:
    await _annoncer(orch, ticket_id, resultat, on_event)
    return _a_relire(controle, resultat)


async def capturer_le_run(
    orch: "Orchestrator",
    resultat: PipelineResult,
    project_id: str,
    on_event: EventCallback,
) -> str | None:
    """Capture the approved run's app from its worktree, when the gate is open.

    Returns why the PR must wait for a human (mode `relire`, step triggered,
    whatever its outcome), None otherwise.
    """
    controle = orch._controle_visuel
    if controle is None or not resultat.approved:
        return None
    if not controle_du(await fichiers_du_diff(orch), controle):
        return None
    ticket_id = resultat.ticket_id
    if orch._worktree is None:
        cause = "pas de worktree : l'app d'un run ne démarre que depuis le sien"
        return await _terminer(orch, controle, ticket_id, ResultatCapture(cause=cause), on_event)
    jeton, manque = _jeton(orch)
    if manque is not None:
        return await _terminer(orch, controle, ticket_id, ResultatCapture(cause=manque), on_event)
    prise = await prendre_les_captures(
        controle, orch._worktree.projet, project_id, ticket_id, jeton
    )
    return await _terminer(orch, controle, ticket_id, prise, on_event)
