"""Pipeline log lines written by the CI watcher.

Sorties de `ci_watcher.py` pour qu'il tienne sous son plafond de longueur :
elles ne lisent aucun état du watcher.
"""
from datetime import UTC, datetime
from pathlib import Path

from tessera.services.git_workspace.journal_attente import attente_vers_fichier
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)


def ajouter_au_log(pipeline_log_path: Path | None, texte: str) -> None:
    """Append one timestamped line to the pipeline log; never raises.

    CIWatcher writes after the checkout is back on the base: a line added to a
    tracked log would leave that tree dirty, so it waits outside the repository
    for the next run instead (ticket-789). An untracked log keeps the append.
    """
    if pipeline_log_path is None:
        return
    ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    line = f"- {ts} — {texte}\n"
    if attente_vers_fichier(pipeline_log_path, line):
        return
    try:
        pipeline_log_path.parent.mkdir(parents=True, exist_ok=True)
        with pipeline_log_path.open("a", encoding="utf-8") as f:
            f.write(line)
    except Exception as exc:  # noqa: BLE001
        _logger.warning("pipeline_log_write_failed", extra={"error": str(exc)})


def ecrire_ligne_log(pipeline_log_path: Path | None, ticket_id: str, message: str) -> None:
    """Append one timestamped line for `ticket_id` to the pipeline log."""
    ajouter_au_log(pipeline_log_path, f"[{ticket_id}] {message}")


def ecrire_log_blocage(
    pipeline_log_path: Path | None, ticket_id: str, pr_number: int, arret: str
) -> None:
    """Write a blocking delivery entry to the pipeline log."""
    ecrire_ligne_log(
        pipeline_log_path,
        ticket_id,
        f"livraison: arrêt — PR #{pr_number} non mergée : {arret[:200]}",
    )


def ecrire_log_merge(
    pipeline_log_path: Path | None, project_id: str, ticket_id: str, pr_number: int
) -> None:
    """Append `[project] ticket PR #N mergée (CI verte)` to the pipeline log."""
    ajouter_au_log(
        pipeline_log_path,
        f"[{project_id}] {ticket_id} PR #{pr_number} mergée (CI verte)",
    )
