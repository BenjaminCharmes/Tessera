"""The pending-reports queue lives outside the repository — ticket-430."""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera import config
from tessera.config import _REPO_ROOT, settings
from tessera.main import app
from tessera.services import signalements_en_attente as attente


def _entree(titre: str) -> dict[str, str]:
    return {"titre": titre, "type": "fix", "corps": f"Corps de {titre}"}


def _ecrire(chemin: Path, titres: list[str]) -> None:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(json.dumps([_entree(t) for t in titres]), encoding="utf-8")


def _lire(chemin: Path) -> list[str]:
    return [e["titre"] for e in json.loads(chemin.read_text(encoding="utf-8"))]


def test_queue_path_is_not_under_the_repository_root() -> None:
    chemin = attente.chemin_attente().resolve()

    assert not chemin.is_relative_to(_REPO_ROOT)


def test_default_state_dir_is_not_under_the_repository_root() -> None:
    assert not config.default_state_dir().resolve().is_relative_to(_REPO_ROOT)


def test_default_state_dir_on_windows_uses_local_app_data(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(config.sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    assert config.default_state_dir() == tmp_path / "Tessera"


def test_default_state_dir_elsewhere_uses_the_local_state_folder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config.sys, "platform", "linux")

    assert config.default_state_dir() == Path.home() / ".local" / "state" / "tessera"


def test_queue_follows_the_state_dir_setting(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(settings, "ide_state_dir", tmp_path / "ailleurs")

    assert attente.chemin_attente() == tmp_path / "ailleurs" / attente.NOM_FICHIER


def test_queueing_creates_the_state_dir(tmp_path: Path) -> None:
    assert not settings.ide_state_dir.exists()

    attente.mettre_en_attente("Un", "fix", "corps")

    assert attente.chemin_attente().is_file()


def test_old_file_is_moved_to_the_new_location_then_removed(tmp_path: Path) -> None:
    ancien = tmp_path / "backend" / attente.NOM_FICHIER
    _ecrire(ancien, ["Premier", "Second"])

    repris = attente.migrer_ancien_fichier(ancien)

    assert repris == 2
    assert _lire(attente.chemin_attente()) == ["Premier", "Second"]
    assert not ancien.exists()


def test_migration_keeps_existing_entries_and_adds_no_duplicate(tmp_path: Path) -> None:
    ancien = tmp_path / "backend" / attente.NOM_FICHIER
    _ecrire(ancien, ["Ancien", "Commun"])
    _ecrire(attente.chemin_attente(), ["Commun", "Recent"])

    repris = attente.migrer_ancien_fichier(ancien)

    assert repris == 1
    assert _lire(attente.chemin_attente()) == ["Ancien", "Commun", "Recent"]
    assert not ancien.exists()


def test_migration_without_an_old_file_changes_nothing(tmp_path: Path) -> None:
    assert attente.migrer_ancien_fichier(tmp_path / "absent.json") == 0
    assert not attente.chemin_attente().exists()


def test_unreadable_old_file_is_set_aside_not_lost(tmp_path: Path) -> None:
    ancien = tmp_path / "backend" / attente.NOM_FICHIER
    ancien.parent.mkdir()
    ancien.write_text("pas du json", encoding="utf-8")

    assert attente.migrer_ancien_fichier(ancien) == 0
    assert ancien.with_suffix(".corrompu").is_file()


def test_old_file_equal_to_the_new_one_is_left_alone(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(settings, "ide_state_dir", tmp_path / "backend")
    _ecrire(attente.chemin_attente(), ["Seul"])

    assert attente.migrer_ancien_fichier(attente.chemin_attente()) == 0
    assert _lire(attente.chemin_attente()) == ["Seul"]


def test_app_startup_migrates_the_old_file() -> None:
    _ecrire(attente.ANCIEN_CHEMIN, ["Avant le demarrage"])

    with TestClient(app):
        pass

    assert _lire(attente.chemin_attente()) == ["Avant le demarrage"]
    assert not attente.ANCIEN_CHEMIN.exists()


def test_gitignore_lists_the_old_queue_path() -> None:
    lignes = (_REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()

    assert "backend/signalements_en_attente.json" in lignes
