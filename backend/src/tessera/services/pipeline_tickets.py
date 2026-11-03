"""Les fiches de tickets d'un run sont vérifiées avant les tests — ticket-526.

Un agent qui écrit des fiches avec `Write` peut reprendre un identifiant déjà
pris : le run a ainsi livré deux fiches `ticket-517` en `todo`. `verifier_tickets`
sait le voir ; ici le pipeline l'appelle après chaque tour de production et
renvoie le tour au producteur, comme pour des tests rouges.

Seuls les problèmes **apparus pendant le run** comptent : l'état est relevé avant
le premier agent, et un défaut ancien qui n'est pas dans le diff ne bloque pas
un run qui n'y touche pas.
"""
import asyncio
from typing import TYPE_CHECKING

from tessera.services.pipeline_run import PipelineRun
from tessera.services.ticket_check import Probleme, verifier_tickets
from tessera.utils.logger import get_logger

if TYPE_CHECKING:
    from tessera.services.orchestrator import Orchestrator

_logger = get_logger(__name__)

# Longueur maximale du détail d'une ligne de journal.
_MAX_DETAIL = 160


def _cle(probleme: Probleme) -> str:
    """Identity of a problem, stable between two checks of the same files."""
    return f"{probleme.chemin}|{probleme.champ}|{probleme.valeur}|{probleme.message}"


def _decrire(probleme: Probleme) -> str:
    valeur = f" = {probleme.valeur!r}" if probleme.valeur is not None else ""
    return f"{probleme.chemin} : {probleme.champ}{valeur} — {probleme.message}"


async def relever_etat_initial(orch: "Orchestrator", run: PipelineRun) -> None:
    """Record the problems the project already has, before any agent runs.

    Une vérification qui échoue laisse la référence vide : le contrôle de fin de
    tour dira alors tout ce qu'il trouve, ce qui ne bloque qu'un run déjà fautif.
    """
    if orch._project_path is None:
        return
    try:
        existants = await asyncio.to_thread(verifier_tickets, orch._project_path)
    except Exception as exc:  # noqa: BLE001 — la vérification ne tue jamais le run
        _logger.warning("ticket_check_baseline_failed", extra={"error": str(exc)})
        return
    run.problemes_tickets_initiaux = frozenset(_cle(p) for p in existants)


async def problemes_nouveaux(orch: "Orchestrator", run: PipelineRun) -> list[Probleme]:
    """Problems of the project's ticket files that were not there before the run."""
    if orch._project_path is None:
        return []
    try:
        trouves = await asyncio.to_thread(verifier_tickets, orch._project_path)
    except Exception as exc:  # noqa: BLE001
        _logger.warning("ticket_check_failed", extra={"error": str(exc)})
        return []
    return [p for p in trouves if _cle(p) not in run.problemes_tickets_initiaux]


def _retour_au_producteur(problemes: list[Probleme]) -> str:
    """What the producer reads on the next turn: the fact, then each problem."""
    lignes = "\n".join(f"- {_decrire(p)}" for p in problemes)
    return (
        f"Les fiches de tickets du projet ont {len(problemes)} problème(s) — "
        "corrige-les avant toute autre chose (un identifiant en double : garde "
        "une seule fiche, supprime l'autre, et prends le numéro suivant le plus "
        f"grand déjà pris).\n{lignes}"
    )


def _ligne_de_journal(ticket_id: str, problemes: list[Probleme]) -> str:
    detail = " ; ".join(_decrire(p) for p in problemes)
    if len(detail) > _MAX_DETAIL:
        detail = detail[: _MAX_DETAIL - 1] + "…"
    return f"[{ticket_id}] tickets: {len(problemes)} problème(s) — {detail}"


async def renvoyer_si_problemes(orch: "Orchestrator", run: PipelineRun) -> bool:
    """Send the round back to its producer when it left ticket problems.

    Returns True when it did: the problems are appended to the run's feedback
    and a line is written to the pipeline log. False — and nothing written —
    when the round left no new problem.
    """
    problemes = await problemes_nouveaux(orch, run)
    if not problemes:
        return False
    run.review_feedback.append(_retour_au_producteur(problemes))
    orch._log(_ligne_de_journal(run.ticket_id, problemes))
    return True
