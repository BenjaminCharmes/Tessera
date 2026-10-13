"""Realign the local base branch after a background merge — ticket-422.

Quand `CIWatcher` merge la dernière PR d'une file, plus aucun run ne passe par
là pour ramener l'arbre local sur la base distante : il reste « behind 1 », et
les services lancés depuis cet arbre servent du code périmé. Cette fonction
fait ce rattrapage, et seulement lui : fast-forward de la base, rien d'autre.

Elle ne touche l'arbre que dans un état sans ambiguïté — sur la branche de
base, avec pour seule modification le journal du pipeline. Tout le reste
(autre branche, autre fichier modifié, pull refusé) laisse l'arbre intact.
"""
import asyncio
from dataclasses import dataclass
from pathlib import Path

from tessera.services import journal_en_attente
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)


@dataclass(frozen=True)
class Realignement:
    """Where to realign: the project root and the base branch to fast-forward."""

    racine: Path
    base_branch: str

_JOURNAL = (Path("memory") / "pipeline-log.md").as_posix()


async def _git(racine: Path, *args: str) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        "git", *args,
        cwd=str(racine),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    return (
        proc.returncode or 0,
        out.decode("utf-8", errors="replace"),
        err.decode("utf-8", errors="replace"),
    )


def _chemin_porcelain(ligne: str) -> str:
    """Path part of a `git status --porcelain` line (renames: the new path)."""
    chemin = ligne[3:].split(" -> ")[-1].strip()
    return chemin.strip('"')


async def _raison_de_refus(racine: Path, base_branch: str) -> str | None:
    """Why the tree must be left alone, or None when it may be realigned."""
    code, sortie, _ = await _git(racine, "rev-parse", "--abbrev-ref", "HEAD")
    if code != 0:
        return "branche courante illisible"
    branche = sortie.strip()
    if branche != base_branch:
        return f"arbre sur la branche {branche}, pas sur {base_branch}"
    # `status --porcelain` donne des chemins relatifs à la racine du dépôt, pas
    # au dossier courant : pour un projet en `git_root: ancestor`, le journal
    # s'écrit `projects/<nom>/memory/pipeline-log.md`. On préfixe donc le
    # journal du chemin du projet dans le dépôt, et on limite le statut au
    # projet (`-- .`) : un autre projet du même dépôt ne nous concerne pas.
    code, prefixe, _ = await _git(racine, "rev-parse", "--show-prefix")
    if code != 0:
        return "position du projet dans le dépôt illisible"
    journal = prefixe.strip() + _JOURNAL
    code, sortie, _ = await _git(racine, "status", "--porcelain", "--", ".")
    if code != 0:
        return "état de l'arbre illisible"
    autres = [
        chemin
        for chemin in map(_chemin_porcelain, sortie.splitlines())
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


async def _avancer(racine: Path, base_branch: str) -> str | None:
    """Set the log aside, pull --ff-only, write the log back; the refusal or None."""
    lignes = await journal_en_attente.mettre_de_cote(racine)
    try:
        code, _, err = await _git(racine, "pull", "--ff-only", "origin", base_branch)
    finally:
        # Réécrit même si le pull a échoué ou levé : le journal ne perd rien.
        journal_en_attente.reecrire(racine, lignes)
    if code != 0:
        return f"pull --ff-only refusé : {err.strip()[:200]}"
    return None
