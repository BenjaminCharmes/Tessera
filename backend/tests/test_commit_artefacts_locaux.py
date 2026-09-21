"""Committer sur un projet dont les artefacts sont locaux — ticket-072."""
import asyncio
from pathlib import Path

import pytest

from tessera.services.git_workspace import GitWorkspaceService


async def _git(cwd: Path, *args: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        "git", *args, cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    assert proc.returncode == 0, err.decode()
    return out.decode()


@pytest.fixture
async def projet_local(tmp_path: Path) -> Path:
    """Un projet en mode artefacts `local` : tickets/ et memory/ sont exclus."""
    p = tmp_path / "projet"
    p.mkdir()
    await _git(p, "init", "-q", "-b", "main")
    await _git(p, "config", "user.email", "t@t.local")
    await _git(p, "config", "user.name", "t")
    (p / "app.py").write_text("x = 1\n", encoding="utf-8")
    await _git(p, "add", "app.py")
    await _git(p, "commit", "-qm", "init")

    (p / ".git" / "info").mkdir(parents=True, exist_ok=True)
    (p / ".git" / "info" / "exclude").write_text(
        "tickets/\nmemory/\nCLAUDE.md\nagents.json\n", encoding="utf-8"
    )
    (p / "tickets" / "todo").mkdir(parents=True)
    (p / "tickets" / "todo" / "t.md").write_text("x\n", encoding="utf-8")
    (p / "memory").mkdir()
    (p / "memory" / "pipeline-log.md").write_text("log\n", encoding="utf-8")
    return p


async def test_le_commit_reussit_quand_les_artefacts_sont_exclus(
    projet_local: Path,
) -> None:
    # Panne vecue le 2026-09-17 : `commit_all` tentait de stager `tickets/` et
    # `memory/pipeline-log.md` pour la tenue de livres. Sur un projet en mode
    # `local` (ADR-021), git refuse un chemin ignore et sort en code 1 — ce qui
    # faisait echouer tout le commit de fin de run, donc tout le run.
    svc = GitWorkspaceService(projet_local)
    await svc.create_branch("ticket-001", "essai")
    (projet_local / "app.py").write_text("x = 2\n", encoding="utf-8")

    sha = await svc.commit_all("feat: ticket-001 — essai")

    assert sha is not None, "le travail du codeur doit etre commite"
    suivis = await _git(projet_local, "ls-files")
    assert "app.py" in suivis
    assert "tickets/" not in suivis and "memory/" not in suivis


async def test_les_artefacts_exclus_ne_sont_pas_commites(projet_local: Path) -> None:
    svc = GitWorkspaceService(projet_local)
    await svc.create_branch("ticket-002", "essai")
    (projet_local / "app.py").write_text("x = 3\n", encoding="utf-8")

    await svc.commit_all("feat: ticket-002 — essai")

    journal = await _git(projet_local, "log", "--format=%s")
    assert journal.count("\n") == 2, journal
