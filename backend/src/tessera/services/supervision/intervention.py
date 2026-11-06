"""Une intervention du superviseur est un run, un commit par action — ticket-854, ADR-080.

Le seul chemin d'écriture du superviseur : un run `supervision` sous le verrou du
projet (ADR-038), dans son worktree, sur la branche `supervision-<horodatage>`
(ADR-018, ADR-056). Le projet tenu par une file ou un run : elle attend sa
fermeture, au plus 30 minutes, puis abandonne sans rien écrire.

Une action fait un commit `chore(supervision): <action> <cible>`, puis une ligne
du journal qui porte son SHA, dans un commit de journal à part : le SHA d'un
commit ne peut pas figurer dans ce commit. `refus_de_chemin` (ticket-851) juge
les fichiers avant le commit ; un fichier hors liste annule tout. La livraison
est celle d'`livrer_intervention` : une PR, jamais de merge (ADR-051, ADR-039).

Toute exception, tout refus, tout commit raté finit en `blocked` avec commit,
jamais un arbre sale (ADR-037) ; rien de ce qui est bloqué ne part.
"""
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from tessera.services.pipeline.pipeline_journal import MODE_SUPERVISION
from tessera.services.pipeline.run_registry import RUN_REGISTRY, RunRegistry
from tessera.services.supervision.intervention_attente import DELAI_MAX_S, prendre_le_projet
from tessera.services.supervision.intervention_chantier import Chantier, ChantierGit, NouveauChantier
from tessera.services.supervision.intervention_controle import JOURNAL, controle_de, refus_avant_commit
from tessera.services.supervision.superviseur_actions import Action
from tessera.services.supervision.superviseur_journal import ajouter_ligne
from tessera.utils.exceptions import decrire_exception
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

PREFIXE_BRANCHE = "supervision-"
_SHA_COURT = 7

Statut = Literal["livre", "local", "rien", "blocked", "abandonne"]


@dataclass(frozen=True)
class Application:
    """What an action reports once it has written in the worktree: its target and a one-line summary."""

    cible: str
    resume: str


@dataclass(frozen=True)
class Resultat:
    """How an intervention ended.

    `livre`: PR opened. `local`: committed, but the project does not let it go
    further (or the delivery stopped: see `raison`). `rien`: nothing changed.
    `blocked`: refused or failed, committed locally, never pushed. `abandonne`:
    the project stayed held until the delay, nothing was written.
    """

    statut: Statut
    action: Action
    cible: str | None = None
    branche: str | None = None
    sha: str | None = None
    pr_number: int | None = None
    raison: str | None = None


def _ligne(texte: str, limite: int = 100) -> str:
    """`texte` on one line, cut at `limite`: fit for a commit subject."""
    return re.sub(r"\s+", " ", texte).strip()[:limite]


async def _bloquer(
    chantier: Chantier, action: Action, branche: str, raison: str, chemins: list[str] | None = None
) -> Resultat:
    """Commit what the tree holds under a `blocked` subject; never raises, never pushes."""
    try:
        restants = chemins if chemins is not None else await chantier.fichiers_modifies()
        if restants:
            await chantier.commiter(f"chore(supervision): {action.value} blocked — {_ligne(raison)}", restants)
    except Exception as exc:  # noqa: BLE001 — l'arbre reste, le worktree se conserve
        _logger.warning("intervention_blocage_non_commite", extra={"erreur": decrire_exception(exc)})
    return Resultat("blocked", action, branche=branche, raison=raison)


async def _commiter_et_journaliser(
    chantier: Chantier, projet: Path, action: Action, application: Application, chemins: list[str], jour: datetime
) -> tuple[str, str]:
    """Commit the action, then its journal line with its SHA; return (action SHA, branch head)."""
    sha = await chantier.commiter(f"chore(supervision): {action.value} {_ligne(application.cible)}", chemins)
    if sha is None:
        raise RuntimeError("le commit de l'action n'a rien commité")
    court = sha[:_SHA_COURT]
    ajouter_ligne(
        projet / "memory", jour=jour.date(), action=action.value, cible=application.cible, sha=court, resume=application.resume,
    )
    tete = await chantier.commiter(f"chore(supervision): journal {action.value} {court}", [JOURNAL])
    return sha, tete or sha


async def _ecrire_et_livrer(
    chantier: Chantier, projet: Path, action: Action, appliquer: Callable[[Path], Awaitable[Application]],
    branche: str, jour: datetime,
) -> Resultat:
    application = await appliquer(projet)
    modifies = await chantier.fichiers_modifies()
    if not modifies:
        return Resultat("rien", action, cible=application.cible, branche=branche)
    refus = refus_avant_commit(modifies, action)
    if refus is not None:
        return await _bloquer(chantier, action, branche, refus, modifies)
    sha, tete = await _commiter_et_journaliser(chantier, projet, action, application, modifies, jour)
    livraison = await chantier.livrer(branche, tete, controle_de(action), f"{action.value} {_ligne(application.cible)}")
    statut: Statut = "livre" if livraison.pr_number is not None else "local"
    return Resultat(statut, action, application.cible, branche, sha, livraison.pr_number, livraison.arret)


async def _sous_verrou(
    project_id: str, action: Action, appliquer: Callable[[Path], Awaitable[Application]],
    chantier: Chantier, jour: datetime,
) -> Resultat:
    branche = f"{PREFIXE_BRANCHE}{jour:%Y%m%d-%H%M%S}"
    try:
        projet = await chantier.ouvrir(branche)
    except Exception as exc:  # noqa: BLE001 — rien n'est écrit : il n'y a rien à commiter
        _logger.warning("intervention_worktree_refuse", extra={"project": project_id, "erreur": decrire_exception(exc)})
        return Resultat("blocked", action, branche=branche, raison=decrire_exception(exc))
    try:
        return await _ecrire_et_livrer(chantier, projet, action, appliquer, branche, jour)
    except Exception as exc:  # noqa: BLE001 — toute exception finit en `blocked` avec commit (ADR-037)
        _logger.warning("intervention_echouee", extra={"project": project_id, "erreur": decrire_exception(exc)})
        return await _bloquer(chantier, action, branche, decrire_exception(exc))
    finally:
        await chantier.fermer()


async def intervenir(
    project_id: str,
    action: Action,
    appliquer: Callable[[Path], Awaitable[Application]],
    *,
    registre: RunRegistry = RUN_REGISTRY,
    nouveau_chantier: NouveauChantier = ChantierGit,
    delai_max_s: float = DELAI_MAX_S,
    maintenant: Callable[[], datetime] = datetime.now,
) -> Resultat:
    """Write for the supervisor: one `supervision` run, one commit for `action`, then its delivery.

    `appliquer` receives the project folder of the run's worktree and writes the
    action's files there; it commits and delivers nothing itself. Waits for the
    project to be free, gives up after `delai_max_s` without writing.
    """
    run = await prendre_le_projet(registre, project_id, MODE_SUPERVISION, f"supervision {action.value}", delai_max_s)
    if run is None:
        _logger.warning("intervention_abandonnee", extra={"project": project_id, "action": action.value})
        return Resultat("abandonne", action, raison="le projet est resté tenu jusqu'au délai maximal : rien n'est écrit")
    try:
        return await _sous_verrou(project_id, action, appliquer, nouveau_chantier(project_id), maintenant())
    finally:
        registre.fermer(run.run_id)
