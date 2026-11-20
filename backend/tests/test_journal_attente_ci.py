"""CIWatcher log lines never leave the base dirty — ticket-789 (queue file: ticket-786)."""

from pathlib import Path

from tessera.services.git_workspace import GitWorkspaceService
from tessera.services.livraison.journal_ci_watcher import ajouter_au_log, ecrire_log_merge
from tessera.services.pipeline import pipeline_branche
from tests.test_journal_attente import _LOG, _attente, _depot, _git, _Orch, _run, _Tickets


async def test_ci_watcher_line_on_a_tracked_log_leaves_the_tree_clean(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    await _depot(root)

    ajouter_au_log(root / _LOG, "[portfolio] ticket-021 PR #27 mergée (CI verte)")

    assert await _git(root, "status", "--porcelain") == ""
    contenu = (await _attente(root)).read_text(encoding="utf-8")
    assert "PR #27 mergée (CI verte)" in contenu
    assert contenu.startswith("- ")


async def test_ci_watcher_line_on_an_untracked_log_is_appended_as_before(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    await _depot(root, suivi=False)

    ecrire_log_merge(root / _LOG, "portfolio", "ticket-021", 27)

    assert "PR #27 mergée (CI verte)" in (root / _LOG).read_text(encoding="utf-8")
    assert not (await _attente(root)).exists()


async def test_a_line_queued_by_ci_watcher_is_rewritten_in_the_next_run_branch(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    await _depot(root)
    ajouter_au_log(root / _LOG, "[portfolio] PR #27 confiée au CIWatcher")
    orch = _Orch(GitWorkspaceService(root), root)
    orch._ticket_svc = _Tickets()  # type: ignore[attr-defined]

    run = _run()
    assert await pipeline_branche.create_branch(orch, run) is None  # type: ignore[arg-type]

    assert "PR #27 confiée au CIWatcher" in (root / _LOG).read_text(encoding="utf-8")
    assert not (await _attente(root)).exists()
