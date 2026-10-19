"""One timestamped line appended to a project's `memory/pipeline-log.md`.

Partagé par `Orchestrator._log` et par ce qui écrit dans le journal sans en
être : le repli d'un provider (ticket-518). Une écriture qui échoue se
journalise et n'arrête rien : le journal est une trace, pas une porte.
"""
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from tessera.utils.logger import get_logger

_logger = get_logger(__name__)


def ajouter_ligne(chemin: Path, message: str) -> None:
    """Appends `- <UTC timestamp> — <message>` to the log at `chemin`."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    ligne = f"- {ts} — {message}\n"
    try:
        chemin.parent.mkdir(parents=True, exist_ok=True)
        with chemin.open("a", encoding="utf-8") as f:
            f.write(ligne)
    except Exception as exc:  # noqa: BLE001 — une trace qui ne s'écrit pas n'arrête rien
        _logger.warning("pipeline_log_write_failed", extra={"error": str(exc)})


def journal_vers(chemin: Path) -> Callable[[str], None]:
    """A writer that appends its messages to the log at `chemin`."""

    def ecrire(message: str) -> None:
        ajouter_ligne(chemin, message)

    return ecrire
