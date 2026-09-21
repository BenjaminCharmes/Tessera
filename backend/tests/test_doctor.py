"""Vérification des prérequis — ticket-056."""
from pathlib import Path

import pytest

from tessera.config import settings
from tessera.doctor import (
    check_prompts_dir,
    check_provider_auth,
    check_workspace,
    run_checks,
)


def test_prompts_manquants_sont_signales(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # La panne de ticket-050 : le chemin ne résolvait jamais, et rien ne le
    # cherchait. Ce contrôle l'aurait attrapée avant le premier lancement.
    monkeypatch.setattr(settings, "ide_prompts_dir", tmp_path / "nulle-part")

    check = check_prompts_dir()

    assert check.ok is False
    assert "IDE_PROMPTS_DIR" in check.fix


def test_prompts_presents_sont_valides() -> None:
    # Le défaut du dépôt doit passer : sinon le contrôle crie au loup.
    assert check_prompts_dir().ok is True


def test_une_clef_api_parasite_est_signalee_en_mode_abonnement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # L'autre panne de ticket-050 : le CLI donne la priorité à la clef sur la
    # session d'abonnement, et échoue en 401.
    monkeypatch.setattr(settings, "llm_provider", "agent_sdk")
    monkeypatch.setattr(settings, "anthropic_api_key", "sk-ant-une-vraie-clef-invalide")

    check = check_provider_auth()

    assert check.ok is False
    assert "priorité" in check.fix


def test_le_placeholder_de_env_example_ne_declenche_pas_d_alerte(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # `.env.example` livre `sk-ant-...` et la doc demande de le recopier :
    # le signaler serait du bruit permanent.
    monkeypatch.setattr(settings, "llm_provider", "agent_sdk")
    monkeypatch.setattr(settings, "anthropic_api_key", "sk-ant-...")

    assert check_provider_auth().ok is True


def test_le_mode_api_exige_une_clef(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "llm_provider", "anthropic_api")
    monkeypatch.setattr(settings, "anthropic_api_key", "")

    check = check_provider_auth()

    assert check.ok is False
    assert "anthropic_api" in check.fix


def test_un_workspace_absent_est_signale(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "ide_workspace_dir", tmp_path / "jamais-cree")
    assert check_workspace().ok is False


def test_les_symlinks_ne_sont_jamais_bloquants() -> None:
    # Le mode `copy` fonctionne partout : une absence de symlink est une
    # information, pas un échec.
    from tessera.doctor import check_symlinks

    assert check_symlinks().ok is True


def test_le_rapport_couvre_tous_les_controles() -> None:
    names = {c.name for c in run_checks()}
    assert names == {
        "Python 3.11+",
        "Fichier .env",
        "Dossier workspace",
        "Prompts des agents",
        "Authentification du provider",
        "Liens symboliques",
        "Toolchain Rust (Tauri)",
        "Ports libres",
    }


def test_rust_absent_n_est_jamais_bloquant() -> None:
    # L'IDE tourne en web sans Tauri : une toolchain absente est une
    # information, pas un échec.
    from tessera.doctor import check_rust

    assert check_rust().ok is True
