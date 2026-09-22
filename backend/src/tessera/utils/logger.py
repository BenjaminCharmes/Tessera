"""Structured JSON logging for the backend.

Le formateur ne sortait que `level/logger/message/exc_info` : les quelque
quatre-vingts `extra={"error": ...}` du backend étaient perdus au moment même
où la panne était loggée, et `ide_log_level` n'était lu nulle part
(ticket-122).
"""
import json
import logging
import sys
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
