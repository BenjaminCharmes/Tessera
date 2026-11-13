"""Worktrees of a project under the agent account live in their own folder — ticket-947."""
from pathlib import Path

import pytest

from tessera.config import settings
from tessera.services.pipeline.reprise_worktrees import reprendre_worktrees_orphelins
from tessera.services.worktrees import dossier_agent
from tessera.services.worktrees.dossier_agent import dossier_des_worktrees, preparer_dossier_agent
from tessera.services.worktrees.run_worktree import creer
from tests.depot_worktree import BRANCHE, construire, git

_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"


@pytest.fixture
def checkout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    repo = construire(tmp_path, monkeypatch)
    monkeypatch.setattr(settings, "ide_worktrees_dir_agent", tmp_path.resolve() / "agent-wt")
    return repo


async def _icacls_muet(args: list[str]) -> tuple[int, str]:
    return 0, ""


async def test_root_is_under_agent_folder_with_account_and_agent_user(
    checkout: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "agent_user", "tessera-agent")
    monkeypatch.setattr(dossier_agent, "_icacls_reel", _icacls_muet)
    wt = await creer(checkout, checkout, "demo", "ticket-1", BRANCHE, "develop", compte_agent=True)
    assert wt.racine == settings.ide_worktrees_dir_agent.resolve() / "demo" / "ticket-1"
    assert wt.racine.is_dir()


async def test_root_stays_under_user_folder_without_account_or_agent_user(
    checkout: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "agent_user", "tessera-agent")
    sans_compte = await creer(checkout, checkout, "demo", "ticket-1", BRANCHE, "develop")
    assert sans_compte.racine.is_relative_to(settings.ide_worktrees_dir.resolve())
    monkeypatch.setattr(settings, "agent_user", "")
    assert dossier_des_worktrees(True) == settings.ide_worktrees_dir
    assert dossier_des_worktrees(False) == settings.ide_worktrees_dir
    assert not settings.ide_worktrees_dir_agent.exists()


async def test_folder_creation_sets_acl_without_inheritance(checkout: Path) -> None:
    appels: list[list[str]] = []

    async def lanceur(args: list[str]) -> tuple[int, str]:
        appels.append(args)
        return 0, ""

    dossier = await preparer_dossier_agent(lanceur, utilisateur="ben")
    assert dossier.is_dir()
    assert appels[0] == [str(dossier), "/inheritance:r"]
    droits = appels[1]
    assert "*S-1-5-18:(OI)(CI)F" in droits
    assert "*S-1-5-32-544:(OI)(CI)F" in droits
    assert "ben:(OI)(CI)M" in droits
    assert not any("tessera-agent" in a for a in droits)
    await preparer_dossier_agent(lanceur, utilisateur="ben")
    assert len(appels) == 2  # un dossier existant n'est pas retouché


async def test_orphan_cleanup_walks_the_agent_folder_too(
    checkout: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "agent_user", "tessera-agent")
    monkeypatch.setattr(dossier_agent, "_icacls_reel", _icacls_muet)
    wt = await creer(checkout, checkout, "demo", "ticket-1", BRANCHE, "develop", compte_agent=True)
    (wt.racine / "suivi.txt").write_text("modifie", encoding="utf-8")
    await reprendre_worktrees_orphelins(
        checkout.parent, settings.ide_worktrees_dir, settings.ide_worktrees_dir_agent
    )
    assert not wt.racine.exists()
    assert git(checkout, "log", "-1", "--format=%s", BRANCHE).startswith("chore: ticket-1 ")


def test_agent_doctor_checks_the_agent_worktrees_folder() -> None:
    texte = (_SCRIPTS / "tessera.ps1").read_text(encoding="utf-8-sig")
    assert "IDE_WORKTREES_DIR_AGENT" in texte
    assert r"C:\ProgramData\Tessera\worktrees" in texte
    assert "Test-DossierWorktreesAgent" in texte
    assert "/inheritance:r" in texte
