"""The test suite never writes the real backend log — ticket-339.

Chaque `TestClient(app)` exécute le `lifespan`, qui ajoutait un gestionnaire
de fichier sur `backend/logs/tessera.log` au logger racine, sans jamais le
retirer : les lignes des tests y atterrissaient, en autant d'exemplaires que
de démarrages, et faisaient tourner les fichiers que le ticket-330 garde pour
retrouver la trace d'un vrai plantage.
"""
import logging
import logging.handlers
from pathlib import Path

from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app


def _vers_le_vrai_journal() -> list[logging.Handler]:
    reel = settings.ide_log_file.resolve()
    return [
        h
        for h in logging.getLogger().handlers
        if isinstance(h, logging.handlers.RotatingFileHandler)
        and Path(h.baseFilename).resolve() == reel
    ]


def test_starting_the_app_in_a_test_does_not_attach_the_real_log() -> None:
    with TestClient(app):
        pass
    with TestClient(app):
        pass

    assert _vers_le_vrai_journal() == []
