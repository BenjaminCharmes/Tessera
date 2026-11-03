"""Realign the local base branch after a background merge — ticket-422.

Quand `CIWatcher` merge la dernière PR d'une file, plus aucun run ne passe par
là pour ramener l'arbre local sur la base distante : il reste « behind 1 », et
les services lancés depuis cet arbre servent du code périmé. Cette fonction
fait ce rattrapage, et seulement lui : fast-forward de la base, rien d'autre.

Elle ne touche l'arbre que dans un état sans ambiguïté — sur la branche de
base, avec pour seule modification le journal du pipeline. Tout le reste
(autre branche, autre fichier modifié, pull refusé) laisse l'arbre intact.
"""
from dataclasses import dataclass
from pathlib import Path

from tessera.services import journal_en_attente
from tessera.services.git_runner import git
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)


@dataclass(frozen=True)
class Realignement:
    """Where to realign: the project root and the base branch to fast-forward."""

    racine: Path
    base_branch: str

_JOURNAL = (Path("memory") / "pipeline-log.md").as_posix()


def _chemin_porcelain(ligne: str) -> str:
    """Path part of a `git status --porcelain` line (renames: the new path)."""
    chemin = ligne[3:].split(" -> ")[-1].strip()
    return chemin.strip('"')


async def _raison_de_refus(racine: Path, base_branch: str) -> str | None:
    """Why the tree must be left alone, or None when it may be realigned."""
    courante = await git(racine, "rev-parse", "--abbrev-ref", "HEAD")
    if not courante.ok:
        return "branche courante illisible"
    branche = courante.out.strip()
    if branche != base_branch:
        return f"arbre sur la branche {branche}, pas sur {base_branch}"
    # `status --porcelain` donne des chemins relatifs à la racine du dépôt, pas
    # au dossier courant : pour un projet en `git_root: ancestor`, le journal
    # s'écrit `projects/<nom>/memory/pipeline-log.md`. On préfixe donc le
    # journal du chemin du projet dans le dépôt, et on limite le statut au
    # projet (`-- .`) : un autre projet du même dépôt ne nous concerne pas.
    prefixe = await git(racine, "rev-parse", "--show-prefix")
    if not prefixe.ok:
        return "position du projet dans le dépôt illisible"
    journal = prefixe.out.strip() + _JOURNAL
    # `-uall` : un dossier non suivi qui ne contient que le journal doit se
    # lire `?? memory/pipeline-log.md`, pas `?? memory/` (ticket-480).
    statut = await git(racine, "status", "--porcelain", "-uall", "--", ".")
    if not statut.ok:
        return "état de l'arbre illisible"
    autres = [
        chemin
        for chemin in map(_chemin_porcelain, statut.out.splitlines())
        if chemin != journal
    ]
    if autres:
        return f"arbre modifié hors du journal ({autres[0]})"
    return None


async def realigner_base(racine: Path, base_branch: str, project_id: str) -> bool:
    """Fast-forward the local base onto its remote; True when it was realigned.

    Never raises: a refusal or a failure is logged as `realignement_ignore`
    with its reason, and the tree is left as found.
    """
    try:
        raison = await _raison_de_refus(racine, base_branch)
        if raison is None:
            raison = await _avancer(racine, base_branch)
    except Exception as exc:  # noqa: BLE001 — le merge reste acquis quoi qu'il arrive
        raison = f"{type(exc).__name__}: {exc}"
    if raison is not None:
        _logger.info(
            "realignement_ignore",
            extra={"project": project_id, "raison": raison},
        )
        return False
    _logger.info("realignement_base", extra={"project": project_id})
    return True


async def _mettre_de_cote_non_suivi(racine: Path, base_branch: str) -> list[str]:
    """Lines of an untracked log that the remote base tracks (ticket-480).

    Le `fetch` ne se fait que si le journal est non suivi : le cas courant
    (journal suivi) ne paie rien de plus. Un fetch qui échoue n'est pas une
    erreur ici : le `pull` qui suit refuse pour la même raison.
    """
    if not await journal_en_attente.journal_non_suivi(racine):
        return []
    if not (await git(racine, "fetch", "origin", base_branch)).ok:
        return []
    return await journal_en_attente.mettre_de_cote_non_suivi(
        racine, f"origin/{base_branch}"
    )


async def _avancer(racine: Path, base_branch: str) -> str | None:
    """Set the log aside, pull --ff-only, write the log back; the refusal or None."""
    lignes = await journal_en_attente.mettre_de_cote(racine)
    lignes += await _mettre_de_cote_non_suivi(racine, base_branch)
    try:
        pull = await git(racine, "pull", "--ff-only", "origin", base_branch)
    finally:
        # Réécrit même si le pull a échoué ou levé : le journal ne perd rien.
        journal_en_attente.reecrire(racine, lignes)
    if not pull.ok:
        return f"pull --ff-only refusé : {pull.err.strip()[:200]}"
    return None
