"""A link born after the diff was read is named at the final commit — ticket-1011."""
from pathlib import Path

import pytest

from tessera.models.ticket import TicketStatus
from tessera.services.git_workspace import GitWorkspaceService
from tessera.services.pipeline.pipeline_outcomes import finish_approved
from tessera.services.worktrees.run_worktree import WorktreeOccupe, creer
from tests.depot_worktree import BRANCHE, construire, git, lier
from tests.test_lien_refuse_fin_de_run import LIEN, _cible, _Orch, _run, depot  # noqa: F401,I001


async def test_a_link_created_before_the_final_commit_blocks_the_approved_run(depot: Path) -> None:  # noqa: F811
    workspace = GitWorkspaceService(depot)
    run = _run()
    run.branch = await workspace.create_branch("ticket-001", "t")
    cible = _cible(depot)
    (depot / "travail.txt").write_text("ok", encoding="utf-8")
    (depot / "docs").mkdir()
    lier(cible, depot / "docs" / "lien-x")
    orch = _Orch(depot, workspace)

    resultat = await finish_approved(orch, run)  # type: ignore[arg-type]

    assert resultat.final_status is TicketStatus.blocked
    assert resultat.approved is False
    assert LIEN in (resultat.arret or "")
    assert "unapproved work" in git(depot, "log", "-1", "--format=%s")
    fichiers = git(depot, "ls-tree", "-r", "--name-only", "HEAD")
    assert "travail.txt" in fichiers
    assert "secret.txt" not in fichiers
    assert (cible / "secret.txt").exists()


async def test_resuming_a_dirty_worktree_names_the_link(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    checkout = construire(tmp_path, monkeypatch)
    wt = await creer(checkout, checkout, "demo", "ticket-1", BRANCHE, "develop")
    dehors = tmp_path / "dehors"
    dehors.mkdir()
    (dehors / "f.txt").write_text("x", encoding="utf-8")
    lier(dehors, wt.racine / "lien-x")

    with pytest.raises(WorktreeOccupe) as erreur:
        await creer(checkout, checkout, "demo", "ticket-1", BRANCHE, "develop")

    assert "lien-x" in str(erreur.value)


async def test_an_unapproved_exit_keeps_its_cause_and_names_the_link(depot: Path) -> None:  # noqa: F811
    from tessera.services.pipeline.pipeline_outcomes import finish_rounds_exhausted

    workspace = GitWorkspaceService(depot)
    run = _run()
    run.branch = await workspace.create_branch("ticket-001", "t")
    cible = _cible(depot)
    (depot / "travail.txt").write_text("ok", encoding="utf-8")
    (depot / "docs").mkdir()
    lier(cible, depot / "docs" / "lien-x")
    orch = _Orch(depot, workspace)

    resultat = await finish_rounds_exhausted(orch, run)  # type: ignore[arg-type]

    assert resultat.final_status is TicketStatus.blocked
    assert "non approuvé après" in (resultat.arret or "")
    assert any(LIEN in ligne for ligne in orch.journal)
    sujet = git(depot, "log", "-1", "--format=%s")
    assert "unapproved work" in sujet and LIEN in sujet
    assert "secret.txt" not in git(depot, "ls-tree", "-r", "--name-only", "HEAD")
    assert (cible / "secret.txt").exists()
