"""Tests du chargeur de system prompts — ticket-051."""
from pathlib import Path

import pytest

from tessera.services.prompt_loader import MissingPromptError, load_system_prompt


def test_charge_le_prompt_quand_il_existe(tmp_path: Path) -> None:
    (tmp_path / "codeur.md").write_text("Tu es le codeur.", encoding="utf-8")
    assert load_system_prompt(tmp_path, "codeur.md") == "Tu es le codeur."


def test_leve_une_erreur_quand_le_prompt_manque(tmp_path: Path) -> None:
    # Un agent privé de son system prompt ne s'arrête pas : il produit du
    # travail hors sujet mais plausible. Échouer net coûte moins cher.
    with pytest.raises(MissingPromptError) as exc:
        load_system_prompt(tmp_path, "planificateur.md")

    message = str(exc.value)
    assert "planificateur.md" in message
    assert str(tmp_path) in message
    assert "IDE_PROMPTS_DIR" in message


def test_leve_une_erreur_quand_le_prompt_est_vide(tmp_path: Path) -> None:
    # Un fichier vide est aussi inexploitable qu'un fichier absent, et plus
    # trompeur : il existe, donc l'ancien garde-fou `exists()` le laissait passer.
    (tmp_path / "reviewer.md").write_text("   \n", encoding="utf-8")

    with pytest.raises(MissingPromptError) as exc:
        load_system_prompt(tmp_path, "reviewer.md")

    assert "vide" in str(exc.value).lower()


def test_l_api_renvoie_le_message_et_non_internal_server_error() -> None:
    # Sans gestionnaire dédié, MissingPromptError remonte en 500
    # "Internal Server Error" : le message qui dit quoi corriger n'atteint
    # jamais l'utilisateur, et la panne reste aussi opaque qu'avant.
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from tessera.main import _missing_prompt_handler

    app = FastAPI()
    app.add_exception_handler(MissingPromptError, _missing_prompt_handler)

    @app.get("/boom")
    def _boom() -> None:
        raise MissingPromptError(Path("/tmp/prompts"), "codeur.md", "fichier absent")

    resp = TestClient(app, raise_server_exceptions=False).get("/boom")

    assert resp.status_code == 500
    detail = resp.json()["detail"]
    assert "codeur.md" in detail
    assert "IDE_PROMPTS_DIR" in detail
