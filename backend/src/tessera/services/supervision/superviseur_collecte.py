"""What the supervisor can do on a project today, and the loop that does it — ticket-859, ADR-080.

Two of the four actions find their input in the project folder alone: the
triage of a raw ticket (`trier`, ticket-855) and the decision on a proposed
lesson or rule (`decider`, ticket-856). Both call a model, so the daily budget
holds them back. The hand-back of a PR and the reopening of a queue
(`reconfier_pr`, `relancer_file`) are model-free; their inputs (the delivered
runs, the interrupted queues) are not read yet, so they offer no candidate.

Each candidate carries the idempotence `sha` of the exact state it acts on: a
raw ticket's body, the set of proposed blocks. A state that changes is a new key.
"""
import hashlib
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path

from tessera.config import settings
from tessera.models.ticket import Ticket, TicketStatus
from tessera.services.noyau.event_hub import EVENT_HUB, EventHub
from tessera.services.pipeline.run_registry import RUN_REGISTRY, RunRegistry
from tessera.services.projets.ticket_service import TicketService
from tessera.services.supervision.intervention import Application, Resultat, intervenir
from tessera.services.supervision.superviseur_actions import Action, Decision
from tessera.services.supervision.superviseur_boucle import SuperviseurBoucle
from tessera.services.supervision.superviseur_boucle_etat import NOM_FICHIER, EtatIdempotence
from tessera.services.supervision.superviseur_boucle_ports import Candidat, depense_du_jour, projets_supervises
from tessera.services.supervision.superviseur_decision_blocs import Genre, blocs_proposes
from tessera.services.supervision.superviseur_decision_ecriture import FICHIERS
from tessera.services.supervision.superviseur_tri import Intervenir, SuperviseurTri, TicketBrut, lister_bruts
from tessera.services.supervision.superviseur_tri_fabrique import superviseur_decision_pour, superviseur_tri_pour
from tessera.utils.exceptions import decrire_exception
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

_GENRES: tuple[Genre, ...] = ("lecon", "regle")


def _empreinte(*textes: str) -> str:
    """A short digest of the texts a candidate acts on."""
    condense = hashlib.sha256()
    for texte in textes:
        condense.update(texte.encode("utf-8"))
        condense.update(b"\0")
    return condense.hexdigest()[:12]


def _intervenir_pour(project_id: str) -> Intervenir:
    async def intervenir_projet(action: Action, appliquer: Callable[[Path], Awaitable[Application]]) -> Resultat:
        return await intervenir(project_id, action, appliquer)

    return intervenir_projet


def _verifier(intervention: Resultat | None) -> None:
    """Raise when an intervention did not write: the key then counts a failure."""
    if intervention is not None and intervention.statut in ("abandonne", "blocked"):
        raise RuntimeError(f"intervention {intervention.statut} : {intervention.raison}")


async def _candidats_tri(project_id: str, project_path: Path) -> list[Candidat]:
    bruts = lister_bruts(project_path)
    if not bruts:
        return []
    service = TicketService(project_path, project_id)
    tickets = await service.list_tickets() + await service.list_archived_tickets()
    ouverts = [t for t in tickets if t.status not in (TicketStatus.done, TicketStatus.cancelled)]
    existants = {t.id for t in tickets}
    tri = superviseur_tri_pour(project_id, project_path, _intervenir_pour(project_id))
    return [
        Candidat(project_id, Action.TRIER, brut.id, _empreinte(brut.corps), False, _trier(tri, brut, ouverts, existants))
        for brut in bruts
    ]


def _trier(tri: SuperviseurTri, brut: TicketBrut, ouverts: list[Ticket], existants: set[str]) -> Callable[[], Awaitable[list[Decision]]]:
    """The execution of one triage, with `brut` bound to it."""

    async def executer() -> list[Decision]:
        resultat = await tri.trier_un(brut, ouverts, existants)
        _verifier(resultat.intervention)
        return [resultat.decision]

    return executer


def _lire(chemin: Path) -> str:
    try:
        return chemin.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _candidats_decision(project_id: str, project_path: Path) -> list[Candidat]:
    memoire = project_path / "memory"
    textes = [b.texte for g in _GENRES for b in blocs_proposes(_lire(memoire / FICHIERS[g]), g)]
    if not textes:
        return []
    decision = superviseur_decision_pour(project_id, project_path, _intervenir_pour(project_id))

    async def executer() -> list[Decision]:
        resultats = await decision.decider(project_id, project_path)
        decisions: list[Decision] = []
        for resultat in resultats:
            if resultat.intervention is not None and resultat.intervention.statut == "blocked":
                raison = f"intervention bloquée : {resultat.intervention.raison}"
                decisions.append(Decision(Action.DECIDER, resultat.bloc.cible, "a_toi", raison[:300]))
                continue
            _verifier(resultat.intervention)
            decisions.append(resultat.decision)
        return decisions

    return [Candidat(project_id, Action.DECIDER, project_id, _empreinte(*textes), False, executer)]


async def collecter(project_id: str, project_path: Path) -> list[Candidat]:
    """The candidates of a project; a source that fails is logged and skipped, the other still reads."""
    candidats: list[Candidat] = []
    try:
        candidats.extend(await _candidats_tri(project_id, project_path))
    except Exception as exc:  # noqa: BLE001 — le tri en panne n'empêche pas la décision
        _logger.warning("superviseur_collecte_tri_en_echec", extra={"project": project_id, "erreur": decrire_exception(exc)})
    try:
        candidats.extend(_candidats_decision(project_id, project_path))
    except Exception as exc:  # noqa: BLE001 — idem dans l'autre sens
        _logger.warning("superviseur_collecte_decision_en_echec", extra={"project": project_id, "erreur": decrire_exception(exc)})
    return candidats


def boucle_du_superviseur(registre: RunRegistry = RUN_REGISTRY, hub: EventHub = EVENT_HUB) -> SuperviseurBoucle:
    """The production loop: the workspace's declared projects, the usage base, the state file."""

    async def depense() -> float:
        return await depense_du_jour(settings.ide_db_path, datetime.now(UTC))

    return SuperviseurBoucle(
        registre,
        hub,
        lambda: projets_supervises(settings.ide_workspace_dir),
        collecter,
        depense,
        EtatIdempotence(settings.ide_state_dir / NOM_FICHIER),
    )
