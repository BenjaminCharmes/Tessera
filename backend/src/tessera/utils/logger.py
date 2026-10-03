"""Structured JSON logging for the backend.

Le formateur ne sortait que `level/logger/message/exc_info` : les quelque
quatre-vingts `extra={"error": ...}` du backend étaient perdus au moment même
où la panne était loggée, et `ide_log_level` n'était lu nulle part
(ticket-122).
"""
import asyncio
import json
import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Any

from tessera.config import settings

# Les attributs qu'un `LogRecord` porte toujours, plus ceux que `Formatter`
# ajoute en formatant. Tout ce qui n'y figure pas vient d'un `extra` de
# l'appelant : c'est ce qu'il faut garder. Construit depuis un vrai record
# plutôt que recopié, pour suivre les versions de Python (`taskName` en 3.12).
_STANDARD_ATTRIBUTES: frozenset[str] = frozenset(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__
) | {"message", "asctime"}


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _STANDARD_ATTRIBUTES and key not in payload:
                payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        # `default=str` : un `Path` ou une exception dans `extra` ne doit pas
        # faire perdre la ligne entière.
        return json.dumps(payload, default=str)


def get_logger(name: str, level: str | None = None) -> logging.Logger:
    """Return a JSON logger; the level defaults to `settings.ide_log_level`."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(_JsonFormatter())
        logger.addHandler(handler)
    resolved = level if level is not None else settings.ide_log_level
    logger.setLevel(getattr(logging, resolved.upper(), logging.INFO))
    return logger


def configure_file_logging(
    log_file: Path,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
) -> None:
    """Add a rotating file handler to the root logger.

    Crée le dossier parent s'il n'existe pas. Les enregistrements de tous les
    loggers du backend remontent au root (propagation activée par défaut) et
    atterrissent dans ce fichier, en plus de la sortie standard.
    """
    log_file.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setFormatter(_JsonFormatter())
    logging.getLogger().addHandler(handler)


def install_asyncio_exception_handler() -> None:
    """Set the current event loop's handler for unhandled task exceptions.

    Doit être appelé depuis un contexte async (loop démarrée). Les exceptions
    non rattrapées d'une tâche asyncio y sont journalisées avec leur trace
    complète plutôt qu'écrites sur stderr par le comportement par défaut.
    """
    _logger = get_logger("tessera.asyncio")

    def _handler(loop: asyncio.AbstractEventLoop, context: dict[str, Any]) -> None:
        exc = context.get("exception")
        if exc:
            _logger.error(
                "asyncio_unhandled_exception",
                exc_info=(type(exc), exc, exc.__traceback__),
                extra={"context_message": context.get("message", "")},
            )
        else:
            _logger.error(
                "asyncio_error",
                extra={"context_message": context.get("message", "")},
            )

    asyncio.get_running_loop().set_exception_handler(_handler)
