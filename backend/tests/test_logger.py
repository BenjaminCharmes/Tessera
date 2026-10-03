"""Le logger JSON garde la cause des pannes — ticket-122, ticket-330."""
import asyncio
import json
import logging
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest

from tessera import config
from tessera.utils.logger import (
    _JsonFormatter,
    configure_file_logging,
    get_logger,
    install_asyncio_exception_handler,
)


def _record(**extra: Any) -> logging.LogRecord:
    record = logging.LogRecord(
        name="tessera.test", level=logging.WARNING, pathname=__file__, lineno=1,
        msg="x", args=(), exc_info=None,
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_les_attributs_extra_sont_dans_le_json() -> None:
    # Quelque quatre-vingts appels du backend passent `extra={"error": ...}`
    # et le formateur ne sortait que level/logger/message : la cause d'une
    # panne était perdue au moment même où on la loggait.
    payload = json.loads(_JsonFormatter().format(_record(error="boom", ticket_id="t-1")))

    assert payload["error"] == "boom"
    assert payload["ticket_id"] == "t-1"
    assert payload["message"] == "x"


def test_les_attributs_standard_ne_sont_pas_dupliques() -> None:
    payload = json.loads(_JsonFormatter().format(_record()))

    assert set(payload) == {"level", "logger", "message"}


def test_une_valeur_extra_non_sérialisable_ne_casse_pas_le_log() -> None:
    # Un `Path` ou une exception dans `extra` ne doit pas faire lever le
    # formateur : perdre le log entier est pire que le rendre en texte.
    payload = json.loads(_JsonFormatter().format(_record(path=Path("a/b"))))

    assert payload["path"] == str(Path("a/b"))


def test_le_niveau_vient_de_la_configuration(monkeypatch: Any) -> None:
    # `ide_log_level` existait dans `Settings` et n'était lu nulle part.
    monkeypatch.setattr(config.settings, "ide_log_level", "DEBUG")

    logger = get_logger("tessera.test.niveau")

    assert logger.level == logging.DEBUG


def test_un_niveau_explicite_l_emporte(monkeypatch: Any) -> None:
    monkeypatch.setattr(config.settings, "ide_log_level", "DEBUG")

    logger = get_logger("tessera.test.explicite", level="ERROR")

    assert logger.level == logging.ERROR


def test_un_warning_avec_extra_sort_sa_cause(capsys: Any) -> None:
    # Le critère du ticket, de bout en bout : un warning avec `extra` produit
    # un JSON qui contient la cause.
    logger = get_logger("tessera.test.bout_en_bout")
    logger.propagate = False

    logger.warning("x", extra={"error": "boom"})

    line = capsys.readouterr().out.strip().splitlines()[-1]
    assert json.loads(line)["error"] == "boom"


# ---------------------------------------------------------------------------
# Tests du logging fichier (ticket-330)
# ---------------------------------------------------------------------------

@pytest.fixture
def _clean_root_file_handlers() -> Generator[None, None, None]:
    """Retire les RotatingFileHandler ajoutés pendant un test."""
    root = logging.getLogger()
    before = set(root.handlers)
    yield
    for h in list(root.handlers):
        if h not in before:
            h.close()
            root.removeHandler(h)


def test_file_handler_writes_log_message(
    tmp_path: Path,
    _clean_root_file_handlers: None,
) -> None:
    # Après configure_file_logging, un message journalisé apparaît dans le fichier.
    log_file = tmp_path / "tessera.log"
    configure_file_logging(log_file)

    logger = get_logger("tessera.test.file_write")
    logger.propagate = True
    logger.warning("hello_file")

    lines = log_file.read_text(encoding="utf-8").strip().splitlines()
    payload = json.loads(lines[-1])
    assert payload["message"] == "hello_file"
    assert payload["level"] == "WARNING"


def test_log_directory_is_created_if_missing(
    tmp_path: Path,
    _clean_root_file_handlers: None,
) -> None:
    # configure_file_logging crée le dossier parent s'il n'existe pas.
    log_file = tmp_path / "sub" / "nested" / "tessera.log"
    assert not log_file.parent.exists()

    configure_file_logging(log_file)

    assert log_file.parent.exists()
    assert log_file.exists()


async def test_asyncio_unhandled_exception_is_logged_with_traceback(
    tmp_path: Path,
    _clean_root_file_handlers: None,
) -> None:
    # Une exception non rattrapée dans une tâche asyncio est écrite dans le
    # fichier de log avec sa trace.
    log_file = tmp_path / "asyncio.log"
    configure_file_logging(log_file)
    install_asyncio_exception_handler()

    # Simuler directement l'appel que la loop ferait pour une tâche échouée.
    exc = RuntimeError("async_task_crash")
    loop = asyncio.get_running_loop()
    loop.call_exception_handler({"exception": exc, "message": "Task exception"})

    # Les handlers sont synchrones : l'écriture est immédiate.
    content = log_file.read_text(encoding="utf-8")
    assert "async_task_crash" in content
    assert "asyncio_unhandled_exception" in content
