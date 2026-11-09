"""Le journal d'un cas « À toi » : une intervention qui ne porte que sa ligne — ticket-868, ADR-080.

Un cas que la boucle range en « À toi » doit se relire sans l'IDE ouvert. Les
lignes du journal d'une action s'écrivent avec son commit (`intervenir`) ; un
cas « À toi » n'a pas d'action à commiter, seulement une ligne. Même mécanique
que `intervenir` : un run `supervision` sous le verrou du projet, un worktree, la
branche `supervision-<horodatage>`, une PR sans merge (ADR-038, ADR-056, ADR-039).

Le commit ne porte que `memory/supervision.md` : `refus_avant_commit` refuse ce
fichier à une action, et ici il n'y en a pas. La livraison relit le diff et refuse
tout autre chemin. Une ligne déjà là (même cible, même résumé) n'est pas doublée.
"""
from collections.abc import Callable, Sequence
from datetime import datetime
from pathlib import Path

from tessera.services.pipeline.pipeline_journal import MODE_SUPERVISION
from tessera.services.pipeline.run_registry import RUN_REGISTRY, RunRegistry
from tessera.services.supervision.intervention import PREFIXE_BRANCHE, Resultat, Statut, bloquer, ligne_unique
from tessera.services.supervision.intervention_attente import DELAI_MAX_S, prendre_le_projet
from tessera.services.supervision.intervention_chantier import Chantier, ChantierGit, NouveauChantier
from tessera.services.supervision.intervention_controle import JOURNAL, controle_du_journal_seul
from tessera.services.supervision.superviseur_actions import Decision
from tessera.services.supervision.superviseur_journal import A_TOI, RESUME_MAX, ajouter_ligne, lire_journal
from tessera.utils.exceptions import decrire_exception
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)


def _cible(decision: Decision) -> str:
    """The decision's target on one line, without the journal's separator."""
    return ligne_unique(decision.cible, 120).replace("|", "/") or "inconnue"


def _resume(decision: Decision) -> str:
    """What the line says: the action concerned and why it went to « À toi »."""
    return ligne_unique(f"{decision.action.value} : {decision.raison}", RESUME_MAX)


def _nouvelles(projet: Path, cas: Sequence[Decision]) -> list[Decision]:
    """The cases whose line (same target, same summary) the journal does not hold yet."""
    deja = {(ligne.cible, ligne.resume) for ligne in lire_journal(projet / "memory") if ligne.action == A_TOI}
    vues: set[tuple[str, str]] = set()
    nouvelles: list[Decision] = []
    for decision in cas:
        cle = (_cible(decision), _resume(decision))
        if cle not in deja and cle not in vues:
            vues.add(cle)
            nouvelles.append(decision)
    return nouvelles


def _titre(cas: Sequence[Decision]) -> str:
    """The commit subject and PR title for these cases."""
    if len(cas) == 1:
        return f"a_toi {ligne_unique(_cible(cas[0]), 80)}"
    return f"a_toi {len(cas)} cases"


async def _ecrire_et_livrer(
    chantier: Chantier, projet: Path, cas: Sequence[Decision], branche: str, jour: datetime
) -> Resultat:
    action = cas[0].action
    nouvelles = _nouvelles(projet, cas)
    if not nouvelles:
        return Resultat("rien", action, branche=branche)
    for decision in nouvelles:
        ajouter_ligne(
            projet / "memory", jour=jour.date(), action=A_TOI, cible=_cible(decision), sha="", resume=_resume(decision),
        )
    modifies = await chantier.fichiers_modifies()
    refus = controle_du_journal_seul(modifies)
    if refus is not None:
        return await bloquer(chantier, action, branche, refus, modifies)
    titre = _titre(nouvelles)
    sha = await chantier.commiter(f"chore(supervision): {titre}", [JOURNAL])
    if sha is None:
        raise RuntimeError("le commit du journal n'a rien commité")
    livraison = await chantier.livrer(branche, sha, controle_du_journal_seul, titre)
    statut: Statut = "livre" if livraison.pr_number is not None else "local"
    return Resultat(statut, action, titre, branche, sha, livraison.pr_number, livraison.arret)


async def _sous_verrou(project_id: str, cas: Sequence[Decision], chantier: Chantier, jour: datetime) -> Resultat:
    branche = f"{PREFIXE_BRANCHE}{jour:%Y%m%d-%H%M%S}"
    action = cas[0].action
    try:
        projet = await chantier.ouvrir(branche)
    except Exception as exc:  # noqa: BLE001 — rien n'est écrit : il n'y a rien à commiter
        _logger.warning("journal_a_toi_worktree_refuse", extra={"project": project_id, "erreur": decrire_exception(exc)})
        return Resultat("blocked", action, branche=branche, raison=decrire_exception(exc))
    try:
        return await _ecrire_et_livrer(chantier, projet, cas, branche, jour)
    except Exception as exc:  # noqa: BLE001 — toute exception finit en `blocked` avec commit (ADR-037)
        _logger.warning("journal_a_toi_echoue", extra={"project": project_id, "erreur": decrire_exception(exc)})
        return await bloquer(chantier, action, branche, decrire_exception(exc))
    finally:
        await chantier.fermer()


async def journaliser_a_toi(
    project_id: str,
    decisions: Sequence[Decision],
    *,
    registre: RunRegistry = RUN_REGISTRY,
    nouveau_chantier: NouveauChantier = ChantierGit,
    delai_max_s: float = DELAI_MAX_S,
    maintenant: Callable[[], datetime] = datetime.now,
) -> Resultat | None:
    """Write one journal line per « À toi » decision, in one `supervision` run; `None` if there is none.

    Only the decisions whose verdict is `a_toi` count: an `agir` already has its
    line (written with its commit), a `rien` has none. Waits for the project to
    be free, gives up after `delai_max_s` without writing.
    """
    cas = [decision for decision in decisions if decision.verdict == "a_toi"]
    if not cas:
        return None
    run = await prendre_le_projet(registre, project_id, MODE_SUPERVISION, f"supervision {_titre(cas)}", delai_max_s)
    if run is None:
        _logger.warning("journal_a_toi_abandonne", extra={"project": project_id})
        return Resultat("abandonne", cas[0].action, raison="le projet est resté tenu jusqu'au délai maximal : rien n'est écrit")
    try:
        return await _sous_verrou(project_id, cas, nouveau_chantier(project_id), maintenant())
    finally:
        registre.fermer(run.run_id)
