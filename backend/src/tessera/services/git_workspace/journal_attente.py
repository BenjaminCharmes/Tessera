"""Pipeline-log lines waiting outside the repository for the next run (tickets 786, 789).

Une ligne de journal écrite quand aucun run n'a de branche à elle (après l'arrêt
d'une file, ou par `CIWatcher` après un merge) tomberait dans un fichier suivi,
sur la base : un arbre sale, et aucun commit n'est permis sur la base. Elle
attend ici, dans un fichier du dossier git commun (hors du suivi, donc sans
règle d'exclusion à poser, et partagé par les worktrees) ; le run suivant la
réécrit dans le journal de sa branche, qui la commite avec sa tenue de livres.
"""
import subprocess
from pathlib import Path

from tessera.services.git_workspace import journal_en_attente
from tessera.services.git_workspace.git_runner import git
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

_NOM = "tessera-pipeline-log-attente"
_JOURNAL = journal_en_attente._JOURNAL


def _chemin(sortie: str, racine: Path) -> Path | None:
    dossier = sortie.strip()
    if not dossier:
        return None
    return (racine / dossier).resolve() / _NOM


def racine_du_journal(journal: Path) -> Path | None:
    """The project folder of ``<racine>/memory/pipeline-log.md``, or None for any other path."""
    if journal.name != _JOURNAL.name or journal.parent.name != _JOURNAL.parent.name:
        return None
    return journal.parent.parent


def attente_vers_fichier(journal: Path, ligne: str) -> bool:
    """Queue ``ligne`` for the next run when the log at ``journal`` is tracked by git.

    True when the line was queued. False — and nothing is written — when the log
    is not tracked (local artifacts, ADR-021), git cannot answer, or the write
    fails: the caller then appends to the log as before. Never raises.
    """
    racine = racine_du_journal(journal)
    if racine is None or not racine.is_dir():
        return False
    try:
        suivi = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", _JOURNAL.as_posix()],
            cwd=racine, capture_output=True, timeout=15, check=False,
        )
        if suivi.returncode != 0:
            return False
        commun = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=racine, capture_output=True, text=True, timeout=15, check=False,
        )
        chemin = _chemin(commun.stdout, racine) if commun.returncode == 0 else None
        if chemin is None:
            return False
        with chemin.open("a", encoding="utf-8") as f:
            f.write(ligne if ligne.endswith("\n") else ligne + "\n")
        return True
    except Exception as exc:  # noqa: BLE001 — le journal est une trace, pas une porte
        _logger.warning("pending_log_queue_failed", extra={"error": str(exc)})
        return False


async def _fichier(racine: Path) -> Path | None:
    commun = await git(racine, "rev-parse", "--git-common-dir")
    return _chemin(commun.out, racine) if commun.ok else None


async def mettre_en_attente(racine: Path, lignes: list[str]) -> bool:
    """Append ``lignes`` to the waiting file; False when they could not be queued."""
    if not lignes:
        return True
    try:
        chemin = await _fichier(racine)
        if chemin is None:
            return False
        with chemin.open("a", encoding="utf-8") as f:
            f.write("".join(f"{ligne}\n" for ligne in lignes))
        return True
    except OSError as exc:
        _logger.warning("pending_log_queue_failed", extra={"error": str(exc)})
        return False


async def reprendre(racine: Path) -> list[str]:
    """Return the queued lines and empty the waiting file; [] when there are none."""
    try:
        chemin = await _fichier(racine)
        if chemin is None or not chemin.is_file():
            return []
        lignes = [
            ligne
            for ligne in chemin.read_text(encoding="utf-8", errors="replace").splitlines()
            if ligne.strip()
        ]
        chemin.unlink()
        return lignes
    except OSError as exc:
        _logger.warning("pending_log_read_failed", extra={"error": str(exc)})
        return []


async def ranger_apres_file(racine: Path) -> None:
    """Move the log lines left uncommitted on the base into the waiting file (ticket-786).

    The log goes back to ``HEAD``. An untracked log is not touched. If the lines
    cannot be queued they are written back, so nothing is lost.
    """
    lignes = await journal_en_attente.mettre_de_cote(racine)
    if lignes and not await mettre_en_attente(racine, lignes):
        journal_en_attente.reecrire(racine, lignes)
