"""Le logger JSON garde la cause des pannes — ticket-122."""
import json
import logging
from pathlib import Path
from typing import Any

from tessera import config
from tessera.utils.logger import _JsonFormatter, get_logger


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
