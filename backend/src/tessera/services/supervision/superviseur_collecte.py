"""What the supervisor can do on a project today, and the loop that does it — ticket-859, ADR-080.

Two of the four actions find their input in the project folder alone: the
triage of a raw ticket (`trier`, ticket-855) and the decision on a proposed
lesson or rule (`decider`, ticket-856). Both call a model, so the daily budget
holds them back. The hand-back of a PR and the reopening of a queue
(`reconfier_pr`, `relancer_file`) are model-free; their candidates come from
`superviseur_collecte_livraison` (ticket-867), which also builds the loop.

Each candidate carries the idempotence `sha` of the exact state it acts on: a
raw ticket's body, the text of one proposed block. A state that changes is a new key.
"""
import hashlib
from collections.abc import Awaitable, Callable
from pathlib import Path

from tessera.models.ticket import Ticket, TicketStatus
from tessera.services.projets.ticket_service import TicketService
from tessera.services.supervision.intervention import Application, Resultat, intervenir
from tessera.services.supervision.superviseur_actions import Action, Decision
from tessera.services.supervision.superviseur_boucle_ports import Candidat
from tessera.services.supervision.superviseur_decision import Passe, SuperviseurDecision
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
    """One candidate per proposed block: a block already decided is not submitted again."""
    memoire = project_path / "memory"
    blocs = [b for g in _GENRES for b in blocs_proposes(_lire(memoire / FICHIERS[g]), g)]
    if not blocs:
        return []
    decision = superviseur_decision_pour(project_id, project_path, _intervenir_pour(project_id))
    passe = Passe()  # partagée : le plafond et l'arrêt sur projet tenu valent pour tout le balayage
    return [
        Candidat(project_id, Action.DECIDER, bloc.cible, _empreinte(bloc.texte), False, _decider(decision, project_id, project_path, bloc.cible, passe))
        for bloc in blocs
    ]


def _decider(decision: SuperviseurDecision, project_id: str, project_path: Path, cible: str, passe: Passe) -> Callable[[], Awaitable[list[Decision]]]:
    """The execution of the decision on one block, with `cible` bound to it."""

    async def executer() -> list[Decision]:
        decisions: list[Decision] = []
        for resultat in await decision.decider_bloc(project_id, project_path, cible, passe):
            if resultat.intervention is not None and resultat.intervention.statut == "blocked":
                raison = f"intervention bloquée : {resultat.intervention.raison}"
                decisions.append(Decision(Action.DECIDER, resultat.bloc.cible, "a_toi", raison[:300]))
                continue
            _verifier(resultat.intervention)
            decisions.append(resultat.decision)
        return decisions

    return executer


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
