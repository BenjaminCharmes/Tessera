"""Retirer un projet de l'IDE — ticket-063.

L'IDE savait ajouter des projets de quatre façons et n'en savait retirer
aucune. La seule issue était de supprimer le dossier à la main — ce qui, pour
un projet importé en `symlink`, revient à peser sur un dossier de travail réel.

Deux actions, jamais confondues :

- **Détacher** — le projet disparaît de l'IDE, les fichiers restent.
- **Supprimer** — le dossier est effacé, sur confirmation qui nomme ce qui est
  perdu.

Et une règle qui ne souffre aucune exception : **aucune suppression ne franchit
un lien symbolique**. `projects/fluentdb` *est* `Desktop/fluentdb` ; effacer le
dossier de travail de l'utilisateur depuis un IDE n'est jamais la bonne
réponse.
"""
import asyncio
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from vibe_ide.utils.logger import get_logger

_logger = get_logger(__name__)

#: Où atterrissent les projets détachés : à côté du workspace, pas dedans.
_DETACHED_DIRNAME = "vibe-ide-detaches"


class RemovalError(Exception):
    """Une opération de retrait a été refusée."""


@dataclass(frozen=True)
class RemovalPlan:
    """Ce que l'utilisateur doit savoir avant de décider."""

    project_id: str
    #: Le chemin réellement visé, liens résolus. C'est lui qu'il faut montrer.
    real_path: str
    is_symlink: bool
    unpushed_commits: int = 0


async def _run_git(cwd: Path, *args: str) -> tuple[int, str]:
    proc = await asyncio.create_subprocess_exec(
        "git", *args,
        cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, _ = await proc.communicate()
    return proc.returncode or 0, out.decode("utf-8", errors="replace")


async def _count_unpushed(project_path: Path) -> int:
    """Commits présents localement et absents de tout remote.

    Sans remote, tout commit est « non poussé » : c'est exactement ce que
    l'utilisateur perdrait, donc c'est ce qu'il faut compter.
    """
    code, _ = await _run_git(project_path, "rev-parse", "--is-inside-work-tree")
    if code != 0:
        return 0

    code, out = await _run_git(
        project_path, "rev-list", "--count", "--branches", "--not", "--remotes"
    )
    if code != 0:
        return 0
    try:
        return int(out.strip() or 0)
    except ValueError:
        return 0


async def describe_removal(project_path: Path) -> RemovalPlan:
    """Décrit ce qu'un retrait toucherait, sans rien modifier."""
    is_symlink = project_path.is_symlink()
    return RemovalPlan(
        project_id=project_path.name,
        real_path=str(project_path.resolve()),
        is_symlink=is_symlink,
        unpushed_commits=await _count_unpushed(project_path),
    )


async def detach_project(project_path: Path) -> str:
    """Retire le projet de l'IDE en préservant les fichiers.

    Un lien est simplement supprimé — sa cible est le dossier de travail de
    l'utilisateur. Une copie ou un clone est déplacé hors du workspace, et le
    chemin de destination est retourné pour que l'UI puisse le dire.
    """
    if not project_path.exists() and not project_path.is_symlink():
        raise RemovalError(f"Projet introuvable : {project_path}")

    if project_path.is_symlink():
        # `unlink` sur un lien de dossier retire le lien, jamais la cible.
        project_path.unlink()
        return str(project_path)

    destination = _detached_destination(project_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(project_path), str(destination))
    _logger.info("project_detached", extra={"destination": str(destination)})
    return str(destination)


def _detached_destination(project_path: Path) -> Path:
    """Un emplacement hors du dépôt de l'IDE, horodaté pour ne rien écraser.

    `projects/../..` désignait la racine du dépôt de vibe-ide : un projet
    détaché y restait, non suivi. Depuis qu'un projet peut travailler dans le
    dépôt parent (ADR-028), un `git add -A` lancé depuis cette racine pouvait
    l'y committer en entier — et « détaché de l'IDE » n'a jamais voulu dire
    « déposé dans le dépôt de l'IDE » (ticket-078).
    """
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    racine = _hors_du_depot(project_path.parent.parent)
    return racine / _DETACHED_DIRNAME / f"{project_path.name}-{stamp}"


def _hors_du_depot(depart: Path) -> Path:
    """Le premier dossier, en remontant, qui ne soit pas dans un dépôt git.

    On ne remonte que tant qu'on voit un `.git` : sur un workspace ordinaire,
    sans dépôt au-dessus, le comportement ne change pas.
    """
    courant = depart
    while (courant / ".git").exists() and courant.parent != courant:
        courant = courant.parent
    return courant


async def delete_project(
    project_path: Path, *, confirmed: bool, workspace: Path | None = None
) -> None:
    """Efface définitivement un projet. Ne franchit jamais un lien symbolique."""
    if not confirmed:
        raise RemovalError(
            "La suppression définitive doit être confirmée : elle efface les "
            "fichiers du projet, y compris les commits non poussés."
        )

    if not project_path.exists() and not project_path.is_symlink():
        raise RemovalError(f"Projet introuvable : {project_path}")

    if workspace is not None:
        resolved_parent = project_path.parent.resolve()
        if resolved_parent != workspace.resolve():
            raise RemovalError(
                f"'{project_path}' n'est pas une entrée du workspace : "
                "la suppression est refusée."
            )

    if project_path.is_symlink():
        # On s'arrête au lien. Effacer sa cible reviendrait à supprimer le
        # dossier de travail de l'utilisateur depuis l'IDE.
        project_path.unlink()
        _logger.info("project_symlink_deleted", extra={"path": str(project_path)})
        return

    shutil.rmtree(project_path)
    _logger.info("project_deleted", extra={"path": str(project_path)})
