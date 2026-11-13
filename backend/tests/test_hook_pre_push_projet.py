"""Tests for the pre-push hook installed in project repositories — ticket-968."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tessera.services.creation_projet.hook_pre_push import EtatHook, installer_hook, installer_sur_tous
from tessera.services.creation_projet.project_importer import ProjectImporter
from tests.conftest import requires_symlinks

_RACINE = Path(__file__).resolve().parents[2]
_PYTHON = f'"{Path(sys.executable).as_posix()}"'
_GIT = ("git", "-c", "user.name=dev", "-c", "user.email=dev@example.com")


def _git(cwd: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [*_GIT, *args], cwd=cwd, capture_output=True, text=True, check=False,
        env={**os.environ, **(env or {})},
    )


def _depot(parent: Path, nom: str) -> Path:
    projet = parent / nom
    projet.mkdir(parents=True)
    assert _git(projet, "init", "-q").returncode == 0
    return projet


def _commit(projet: Path, contenu: str, message: str = "chore: add notes") -> None:
    (projet / "notes.txt").write_text(contenu, encoding="utf-8")
    _git(projet, "add", "notes.txt")
    assert _git(projet, "commit", "-q", "-m", message).returncode == 0


def _pousser(projet: Path, distant: Path) -> subprocess.CompletedProcess[str]:
    env = {"FORBIDDEN_TERMS": "zorglub", "SECRETS_SOURCE": "env"}
    _git(projet, "remote", "add", "origin", str(distant))
    return _git(projet, "push", "origin", "HEAD:refs/heads/main", env=env)


def _distant(tmp_path: Path) -> Path:
    distant = tmp_path / "distant.git"
    subprocess.run(["git", "init", "-q", "--bare", str(distant)], check=True)
    return distant


def test_push_with_forbidden_term_is_refused(tmp_path: Path) -> None:
    projet = _depot(tmp_path, "p")
    assert installer_hook(projet, _RACINE, _PYTHON) is EtatHook.INSTALLE
    # Le terme est dans le message : sur une nouvelle branche le hook de Tessera
    # ne relit pas le contenu (voir les notes du ticket).
    _commit(projet, "contenu neutre\n", "chore: zorglub")
    resultat = _pousser(projet, _distant(tmp_path))
    assert resultat.returncode != 0


def test_push_without_forbidden_term_passes(tmp_path: Path) -> None:
    projet = _depot(tmp_path, "p")
    installer_hook(projet, _RACINE, _PYTHON)
    _commit(projet, "rien a signaler\n")
    resultat = _pousser(projet, _distant(tmp_path))
    assert resultat.returncode == 0, resultat.stderr


def test_professional_project_gets_no_hook(tmp_path: Path) -> None:
    projet = _depot(tmp_path, "p")
    (projet / "agents.json").write_text(json.dumps({"confidentiality": "professional"}), encoding="utf-8")
    assert installer_hook(projet, _RACINE) is EtatHook.PROFESSIONNEL
    assert not (projet / ".git" / "hooks" / "pre-push").exists()


def test_existing_different_hook_is_left_alone(tmp_path: Path) -> None:
    projet = _depot(tmp_path, "p")
    existant = projet / ".git" / "hooks" / "pre-push"
    existant.parent.mkdir(exist_ok=True)
    existant.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    assert installer_hook(projet, _RACINE) is EtatHook.DIFFERENT
    assert existant.read_text(encoding="utf-8") == "#!/bin/sh\nexit 0\n"


def test_second_install_reports_already_present(tmp_path: Path) -> None:
    projet = _depot(tmp_path, "p")
    assert installer_hook(projet, _RACINE) is EtatHook.INSTALLE
    assert installer_hook(projet, _RACINE) is EtatHook.DEJA_PRESENT


def test_folder_without_repository_is_reported(tmp_path: Path) -> None:
    (tmp_path / "vide").mkdir()
    assert installer_hook(tmp_path / "vide", _RACINE) is EtatHook.SANS_DEPOT


def test_install_on_all_projects_names_each(tmp_path: Path) -> None:
    _depot(tmp_path, "a")
    (tmp_path / "b").mkdir()
    etats = installer_sur_tous(tmp_path)
    assert etats == {"a": EtatHook.INSTALLE, "b": EtatHook.SANS_DEPOT}


@requires_symlinks
@pytest.mark.asyncio
async def test_import_installs_the_hook(tmp_path: Path) -> None:
    source = _depot(tmp_path / "sources", "mon-projet")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    await ProjectImporter(workspace).import_project(source, "symlink")
    assert (source / ".git" / "hooks" / "pre-push").is_file()
