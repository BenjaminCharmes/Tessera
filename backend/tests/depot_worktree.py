"""Throwaway repository with a local origin, shared by the run-worktree tests (ticket-523)."""
import subprocess
import sys
from pathlib import Path

import pytest

from tessera.config import settings

BRANCHE = "ticket-1-demo"


def git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com",
         "-c", "commit.gpgsign=false", *args],
        cwd=cwd, check=True, capture_output=True, text=True,
    )
    return result.stdout.strip()


def _commit(repo: Path, nom: str, contenu: str) -> None:
    (repo / nom).write_text(contenu, encoding="utf-8")
    git(repo, "add", nom)
    git(repo, "commit", "-m", f"add {nom}")


def construire(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A checkout on `develop` whose origin holds it; ignored files sit beside tracked ones."""
    base = tmp_path.resolve()
    origin = base / "origin.git"
    origin.mkdir()
    git(origin, "init", "--bare", "-b", "develop")
    repo = base / "checkout"
    repo.mkdir()
    git(repo, "init", "-b", "develop")
    _commit(repo, ".gitignore", "node_modules/\ncache/\nsecret.cfg\n")
    _commit(repo, "suivi.txt", "suivi")
    git(repo, "remote", "add", "origin", str(origin))
    git(repo, "push", "origin", "develop")
    (repo / "node_modules" / "pkg").mkdir(parents=True)
    (repo / "node_modules" / "pkg" / "index.js").write_text("temoin", encoding="utf-8")
    (repo / "cache").mkdir()
    (repo / "cache" / "a.txt").write_text("cache", encoding="utf-8")
    (repo / "secret.cfg").write_text("secret", encoding="utf-8")
    (repo / "pas-suivi.txt").write_text("libre", encoding="utf-8")
    monkeypatch.setattr(settings, "ide_worktrees_dir", base / "worktrees")
    return repo


def lier(cible: Path, lien: Path) -> None:
    """A junction on Windows, a symlink elsewhere: what `populate` itself creates."""
    if sys.platform == "win32":
        import _winapi
        _winapi.CreateJunction(str(cible), str(lien))
    else:
        lien.symlink_to(cible, target_is_directory=True)
