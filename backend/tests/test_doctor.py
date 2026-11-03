"""Vérification des prérequis — ticket-056."""
import subprocess
from pathlib import Path

import pytest

from tessera.config import settings
from tessera.doctor import (
    check_checkout,
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
        "Checkout sur develop",
    }


def test_rust_absent_n_est_jamais_bloquant() -> None:
    # L'IDE tourne en web sans Tauri : une toolchain absente est une
    # information, pas un échec.
    from tessera.doctor import check_rust

    assert check_rust().ok is True


def _git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return done.stdout.strip()


def _clone_on_develop(tmp_path: Path) -> Path:
    """A clone on `develop` whose `origin` is a local bare repository."""
    origin = tmp_path / "origin.git"
    seed = tmp_path / "seed"
    seed.mkdir()
    _git(seed, "init", "-b", "develop")
    _git(seed, "commit", "--allow-empty", "-m", "first")
    subprocess.run(["git", "clone", "--bare", str(seed), str(origin)], check=True, capture_output=True)
    clone = tmp_path / "clone"
    subprocess.run(["git", "clone", str(origin), str(clone)], check=True, capture_output=True)
    return clone


def test_checkout_fails_on_a_branch_other_than_develop_and_names_it(tmp_path: Path) -> None:
    clone = _clone_on_develop(tmp_path)
    _git(clone, "switch", "-c", "ticket-999-autre")

    check = check_checkout(clone)

    assert check.ok is False
    assert "ticket-999-autre" in check.detail
    assert "git switch develop" in check.fix


def test_checkout_fails_when_head_differs_from_origin_develop(tmp_path: Path) -> None:
    clone = _clone_on_develop(tmp_path)
    _git(clone, "commit", "--allow-empty", "-m", "local only")

    check = check_checkout(clone)

    assert check.ok is False
    assert "1 en avance" in check.detail


def test_checkout_fails_when_behind_origin_develop_and_gives_the_pull_command(
    tmp_path: Path,
) -> None:
    clone = _clone_on_develop(tmp_path)
    other = tmp_path / "other"
    subprocess.run(["git", "clone", str(tmp_path / "origin.git"), str(other)], check=True, capture_output=True)
    _git(other, "commit", "--allow-empty", "-m", "upstream")
    _git(other, "push", "origin", "develop")

    check = check_checkout(clone)

    assert check.ok is False
    assert "1 en retard" in check.detail
    assert "pull --ff-only" in check.fix


def test_checkout_passes_when_head_equals_origin_develop(tmp_path: Path) -> None:
    assert check_checkout(_clone_on_develop(tmp_path)).ok is True


def test_checkout_fails_outside_a_git_repository(tmp_path: Path) -> None:
    assert check_checkout(tmp_path).ok is False
