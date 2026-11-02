"""Documentation of an approved run — ticket-686.

`Orchestrator.run_pipeline` reaches this module through `apres_approbation`.
The batch documentation runs once, on the branch of the run, before its
delivery (ADR-035, ADR-018).
"""
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

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


@dataclass
class _Lot:
    """What one documentation pass reported, read tolerantly."""

    fichiers: list[str]
    refus: list[str]
    tickets: list[str]
    ecartes: list[str]
    tronque: bool
    marqueur_ecrit: bool
    correction: bool

    @classmethod
    def lire(cls, doc: object) -> "_Lot":
        # getattr : les doubles de documentation des tests n'ont pas tous
        # chaque champ.
        return cls(
            fichiers=list(getattr(doc, "fichiers_modifies", []) or []),
            refus=list(getattr(doc, "refus", []) or []),
            tickets=list(getattr(doc, "tickets", []) or []),
            ecartes=list(getattr(doc, "ecartes", []) or []),
            tronque=bool(getattr(doc, "tronque", False)),
            marqueur_ecrit=bool(getattr(doc, "marqueur_ecrit", False)),
            correction=bool(getattr(doc, "tour_de_correction", False)),
        )


async def documenter_le_run(
    orch: "Orchestrator", resultat: PipelineResult, on_event: EventCallback
) -> None:
    """Update the documentation after an approved run, on its branch.

    The batch stays the marker's: a run that follows five undocumented tickets
    documents them all. The documentation is committed here, on the run's
    branch, to leave in its PR — at the end of a queue it used to stay on disk
    uncommitted and the next run refused the dirty tree (ADR-018). A failure
    does not break the run: the work is committed, and losing its result for a
    late documentation would be disproportionate (ticket-198).
    """
    if orch._documenter is None:
        return
    await on_event(
        OrchestratorEvent(
            type=EventType.DOCUMENTATION_STARTED, ticket_id=resultat.ticket_id
        )
    )
    t0 = time.monotonic()
    try:
        doc = await orch._documenter()
    except Exception as exc:  # noqa: BLE001 — voir la docstring
        await _echec(orch, resultat, exc, on_event)
        return
    lot = _Lot.lire(doc)
    _journaliser(orch, resultat, lot, int((time.monotonic() - t0) * 1000))
    await _commiter(orch, resultat, lot)
    await _signaler(resultat, lot, on_event)


async def _echec(
    orch: "Orchestrator",
    resultat: PipelineResult,
    exc: Exception,
    on_event: EventCallback,
) -> None:
    _logger.warning("documentation_echouee", extra={"erreur": str(exc)})
    orch._log(f"[{resultat.ticket_id}] documentation: échec — {str(exc)[:80]}")
    await on_event(
        OrchestratorEvent(
            type=EventType.DOCUMENTATION_FAILED,
            ticket_id=resultat.ticket_id,
            data={"error": str(exc)},
        )
    )


def _journaliser(
    orch: "Orchestrator", resultat: PipelineResult, lot: _Lot, doc_ms: int
) -> None:
    # « 0 fichier(s) » seul cachait six refus d'affilée sur démineur, chacun
    # pour plusieurs minutes de calcul (ticket-342).
    motifs = "".join(f" — refusé : {r[:160]}" for r in lot.refus)
    # Un tour de correction coûte un appel de plus : le journal le dit (ticket-395).
    correction = " — après tour de correction" if lot.correction else ""
    orch._log(
        f"[{resultat.ticket_id}] documentation: {len(lot.fichiers)} fichier(s)"
        f" ({doc_ms}ms){correction}{motifs}"
    )
    # Un ticket sans diff retrouvable n'est pas documenté : le journal le
    # dit, ticket par ticket (ticket-541).
    for ecarte in lot.ecartes:
        orch._log(f"[{ecarte}] documentation: pas de diff retrouvable, non documenté")


async def _commiter(
    orch: "Orchestrator", resultat: PipelineResult, lot: _Lot
) -> None:
    """Commit when doc files changed **or** the marker was rewritten.

    Either way the tree must stay clean before delivery (ADR-018, ticket-213).
    """
    if not (lot.fichiers or lot.marqueur_ecrit):
        return
    if orch._git_workspace is None or resultat.branch is None:
        return
    try:
        await orch._git_workspace.commit_all(
            f"docs: update documentation for {resultat.ticket_id}"
        )
    except Exception as exc:  # noqa: BLE001
        _logger.warning("documentation_commit_echoue", extra={"erreur": str(exc)})
        lot.refus.append(f"commit : {exc}")


async def _signaler(
    resultat: PipelineResult, lot: _Lot, on_event: EventCallback
) -> None:
    if not (lot.fichiers or lot.refus or lot.tronque or lot.ecartes):
        return
    await on_event(
        OrchestratorEvent(
            type=EventType.DOC_UPDATED,
            ticket_id=resultat.ticket_id,
            data={
                "fichiers": lot.fichiers,
                "refus": lot.refus,
                "tickets": lot.tickets,
                "tronque": lot.tronque,
                "ecartes": lot.ecartes,
            },
        )
    )
