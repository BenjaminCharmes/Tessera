"""`sha_distant` sur un clone qui ne suit que `main` — ticket-517.

Couverture :
- un push de la branche du ticket ne crée aucune référence locale
  `origin/<branche>` quand le refspec est réduit : le SHA se lit sur le distant ;
- un distant injoignable donne `None`, jamais une exception ;
- une branche absente du distant donne `None` ;
- un clone de Tessera porte le refspec complet ;
- la livraison d'un dépôt au refspec réduit renseigne `pushed_sha`.
"""
import asyncio
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from tessera.services.git_clone import GitCloneService
from tessera.services.git_workspace import GitWorkspaceService
from tessera.services.livraison import Livraison, LivraisonService

_BRANCHE = "ticket-001-slug"
_REFSPEC_COMPLET = "+refs/heads/*:refs/remotes/origin/*"


async def _git(cwd: Path, *args: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        "git", *args, cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    assert proc.returncode == 0, f"git {' '.join(args)} : {err.decode()}"
    return out.decode().strip()


async def _commit(cwd: Path, fichier: str, contenu: str) -> str:
    (cwd / fichier).write_text(contenu, encoding="utf-8")
    await _git(cwd, "add", fichier)
    await _git(cwd, "commit", "-q", "-m", f"change {fichier}")
    return await _git(cwd, "rev-parse", "HEAD")


async def _distant(tmp_path: Path) -> Path:
    """A bare remote holding `main`, fed from a throw-away working repo."""
    amont = tmp_path / "amont"
    amont.mkdir()
    await _git(amont, "init", "-q", "-b", "main")
    await _git(amont, "config", "user.email", "test@tessera.local")
    await _git(amont, "config", "user.name", "Tessera test")
    await _commit(amont, "README.md", "# depot\n")
    distant = tmp_path / "distant.git"
    await _git(tmp_path, "clone", "-q", "--bare", str(amont), str(distant))
    return distant


async def _clone_reduit(tmp_path: Path, distant: Path) -> Path:
    """A clone as `--depth=1` used to leave it: the refspec follows `main` only."""
    clone = tmp_path / "clone"
    await _git(
        tmp_path, "clone", "-q", "--depth=1", "--single-branch",
        distant.as_uri(), str(clone),
    )
    await _git(clone, "config", "user.email", "test@tessera.local")
    await _git(clone, "config", "user.name", "Tessera test")
    refspec = await _git(clone, "config", "remote.origin.fetch")
    assert refspec == "+refs/heads/main:refs/remotes/origin/main"
    await _git(clone, "checkout", "-q", "-b", _BRANCHE)
    return clone


@pytest.fixture
async def clone_reduit(tmp_path: Path) -> Path:
    return await _clone_reduit(tmp_path, await _distant(tmp_path))


async def test_sha_distant_reads_the_remote_when_refspec_follows_main_only(
    clone_reduit: Path,
) -> None:
    tete = await _commit(clone_reduit, "code.py", "x = 1\n")
    await _git(clone_reduit, "push", "-q", "origin", _BRANCHE)

    local = await asyncio.create_subprocess_exec(
        "git", "rev-parse", "--verify", "--quiet", f"refs/remotes/origin/{_BRANCHE}",
        cwd=str(clone_reduit),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    await local.communicate()
    assert local.returncode != 0  # le piège du ticket : aucune référence locale

    assert await GitWorkspaceService(clone_reduit).sha_distant(_BRANCHE) == tete


async def test_sha_distant_is_none_when_branch_is_not_on_the_remote(
    clone_reduit: Path,
) -> None:
    await _commit(clone_reduit, "code.py", "x = 1\n")

    assert await GitWorkspaceService(clone_reduit).sha_distant(_BRANCHE) is None


async def test_sha_distant_is_none_when_remote_is_unreachable(
    clone_reduit: Path, tmp_path: Path
) -> None:
    await _commit(clone_reduit, "code.py", "x = 1\n")
    absent = tmp_path / "n-existe-pas.git"
    await _git(clone_reduit, "remote", "set-url", "origin", str(absent))

    assert await GitWorkspaceService(clone_reduit).sha_distant(_BRANCHE) is None


async def test_clone_by_tessera_follows_every_branch(tmp_path: Path) -> None:
    distant = await _distant(tmp_path)
    dest = tmp_path / "clone-tessera"
    service = GitCloneService(tmp_path, MagicMock())

    await service._run_clone(distant.as_uri(), dest)

    assert await _git(dest, "config", "remote.origin.fetch") == _REFSPEC_COMPLET


class _WorkflowQuiPousse:
    """Opens no real PR, but really pushes the branch, as the workflow does."""

    def __init__(self, git: GitWorkspaceService) -> None:
        self._git = git

    async def open_pull_request(self, **kwargs: str | None) -> MagicMock:
        branche = kwargs["branch"]
        assert branche is not None
        await self._git.push_branch(branche)
        return MagicMock(pr_number=7)


class _GitSansRebase:
    """The real `sha_distant`; the other steps of phase 1 are no-ops."""

    def __init__(self, reel: GitWorkspaceService) -> None:
        self._reel = reel

    async def sync_base_depuis_distant(self, base_branch: str) -> str | None:
        return None

    async def commit_bookkeeping(self) -> None:
        return None

    async def commits_hors_rangement(self, depuis: str) -> list[str]:
        return []

    async def rejouer_sur(self, base: str, resolveur: object = None) -> tuple[str, ...]:
        return ()

    async def sha_distant(self, branch: str) -> str | None:
        return await self._reel.sha_distant(branch)


async def test_delivery_on_reduced_refspec_records_pushed_sha(
    clone_reduit: Path,
) -> None:
    tete = await _commit(clone_reduit, "code.py", "x = 1\n")
    reel = GitWorkspaceService(clone_reduit)
    (clone_reduit / "agents.json").write_text('{"autonomy": "pr"}', encoding="utf-8")
    service = LivraisonService(
        git_workspace=_GitSansRebase(reel),
        workflow=_WorkflowQuiPousse(reel),  # type: ignore[arg-type]
        project_path=clone_reduit,
        base_branch="main",
    )

    livraison: Livraison = await service.livrer_phase_1(
        ticket_id="ticket-001", ticket_title="Du travail", ticket_body="",
        branch=_BRANCHE, approuve=True,
    )

    assert livraison.pr_number == 7
    assert livraison.pushed_sha == tete
