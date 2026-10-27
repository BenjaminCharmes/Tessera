"""A pipeline-log line left by the CIWatcher no longer blocks the next ticket — ticket-610.

La ligne « livraison: arrêt — PR non mergée » est écrite en fond, après le
commit du ticket précédent : elle reste non commitée dans le checkout, et git
refuse alors de rebaser la branche reprise du ticket suivant.
"""
import asyncio
from pathlib import Path

import pytest

from tessera.services.git_workspace import GitWorkspaceService
from tessera.services.git_workspace.erreurs import GitCommandError
from tessera.services.git_workspace.noms import _branch_name

_LOG = Path("memory") / "pipeline-log.md"
_LIGNE = "- 2026-10-27 17:47:00 UTC — [ticket-577] livraison: arrêt — PR #691 non mergée"
_MESSAGE_RANGEMENT = "chore: tessera pipeline bookkeeping"
_BRANCHE = _branch_name("ticket-569", "Late branch")


async def _git(cwd: Path, *args: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        "git", *args,
        cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    assert proc.returncode == 0, stderr.decode()
    return stdout.decode().strip()


async def _depot_avec_branche_en_retard(root: Path) -> tuple[GitWorkspaceService, str]:
    """A ticket branch checked out, one commit behind the base, log line pending."""
    root.mkdir()
    await _git(root, "init", "-q")
    await _git(root, "config", "user.email", "test@tessera.local")
    await _git(root, "config", "user.name", "Tessera test")
    (root / "memory").mkdir()
    (root / _LOG).write_text("# log\n", encoding="utf-8")
    (root / "code.py").write_text("x = 1\n", encoding="utf-8")
    await _git(root, "add", ".")
    await _git(root, "commit", "-q", "-m", "init")
    base0 = await _git(root, "rev-parse", "HEAD")

    await _git(root, "checkout", "-q", "-b", _BRANCHE)
    (root / "feature.py").write_text("y = 1\n", encoding="utf-8")
    await _git(root, "add", ".")
    await _git(root, "commit", "-q", "-m", "ticket work")

    await _git(root, "checkout", "-q", "-b", "develop", base0)
    (root / "autre.py").write_text("z = 1\n", encoding="utf-8")
    await _git(root, "add", ".")
    await _git(root, "commit", "-q", "-m", "base advances")
    base1 = await _git(root, "rev-parse", "HEAD")

    await _git(root, "checkout", "-q", _BRANCHE)
    with (root / _LOG).open("a", encoding="utf-8") as f:
        f.write(_LIGNE + "\n")

    workspace = GitWorkspaceService(root)
    workspace._base_ref = base1  # type: ignore[assignment]
    return workspace, base1


async def test_log_line_is_carried_through_the_rebase_and_committed(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    workspace, base = await _depot_avec_branche_en_retard(root)

    branche = await workspace.create_branch("ticket-569", "Late branch")

    assert branche == _BRANCHE
    assert await _git(root, "merge-base", "HEAD", base) == base
    assert _LIGNE in await _git(root, "show", f"HEAD:{_LOG.as_posix()}")
    assert await _git(root, "log", "-1", "--format=%s") == _MESSAGE_RANGEMENT
    assert await _git(root, "status", "--porcelain", "--untracked-files=no") == ""


async def test_carrying_the_log_commits_nothing_else(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    workspace, _ = await _depot_avec_branche_en_retard(root)

    await workspace.create_branch("ticket-569", "Late branch")

    fichiers = await _git(root, "show", "--name-only", "--format=", "HEAD")
    assert fichiers == _LOG.as_posix()


async def test_another_modified_file_still_fails_the_branch_preparation(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    workspace, _ = await _depot_avec_branche_en_retard(root)
    (root / "feature.py").write_text("y = 2\n", encoding="utf-8")

    with pytest.raises(GitCommandError):
        await workspace.create_branch("ticket-569", "Late branch")

    # Rien n'est perdu pour autant : la ligne reste dans le journal, non commitée.
    assert _LIGNE in (root / _LOG).read_text(encoding="utf-8")
    assert _LIGNE not in await _git(root, "show", f"HEAD:{_LOG.as_posix()}")


async def test_a_clean_tree_creates_the_branch_without_an_extra_commit(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    workspace, _ = await _depot_avec_branche_en_retard(root)
    await _git(root, "checkout", "-q", "--", _LOG.as_posix())

    await workspace.create_branch("ticket-569", "Late branch")

    assert await _git(root, "log", "-1", "--format=%s") == "ticket work"
