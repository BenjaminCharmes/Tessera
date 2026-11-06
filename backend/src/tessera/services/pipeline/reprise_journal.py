"""Journal line written by the startup recovery for an approved, undelivered ticket."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from tessera.utils.logger import get_logger

_logger = get_logger(__name__)


def journaliser_approuve_non_livre(project_path: Path, ticket_id: str) -> None:
    """Appends an 'approved but undelivered' entry to memory/pipeline-log.md."""
    ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    ligne = (
        f"- {ts} — [{ticket_id}] approuvé mais non livré : livraison à reprendre\n"
    )
    log_path = project_path / "memory" / "pipeline-log.md"
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(ligne)
    except Exception as exc:
        _logger.warning(
            "reprise_journal_echec",
            extra={
                "project_path": str(project_path),
                "ticket_id": ticket_id,
                "error": str(exc),
            },
        )
