"""No program named in a git config runs when the backend commits or diffs — ticket-965."""
import subprocess
from pathlib import Path

import pytest

from tessera.models.ticket import TicketStatus
from tessera.services.noyau.git_commande import build_command
from tessera.services.noyau.pipeline_events import PipelineResult
from tessera.services.pipeline.pipeline_empreinte import config_git_changee, gardee
from tests.doubles_git import GitWorkspaceDouble
from tests.test_empreinte_run import _Orch, _run

_FORCES = ("commit.gpgsign=false", "tag.gpgSign=false", "gpg.program=",
           "core.sshCommand=", "diff.external=", "core.pager=cat")


def _git(depot: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=depot, check=True, capture_output=True)


@pytest.mark.parametrize("args", [("status",), ("commit", "-m", "x")])
def test_build_command_neutralizes_program_keys(args: tuple[str, ...]) -> None:
    commande = build_command(args)
    for reglage in _FORCES:
        assert reglage in commande


@pytest.mark.parametrize("sous_commande", ["diff", "show", "log"])
def test_diff_commands_carry_no_ext_diff_and_no_textconv(sous_commande: str) -> None:
    commande = build_command((sous_commande, "HEAD"))
    assert "--no-ext-diff" in commande
    assert "--no-textconv" in commande
    assert commande.index("--no-ext-diff") == commande.index(sous_commande) + 1


def test_status_gets_no_diff_options() -> None:
    assert "--no-ext-diff" not in build_command(("status",))


def test_commit_with_gpgsign_does_not_run_the_signing_program(tmp_path: Path) -> None:
    depot = tmp_path / "depot"
    depot.mkdir()
    temoin = tmp_path / "temoin"
    script = tmp_path / "faux_gpg.sh"
    script.write_text(f"#!/bin/sh\necho x > '{temoin.as_posix()}'\nexit 1\n", encoding="utf-8")
    _git(depot, "init", "-q")
    _git(depot, "config", "user.email", "a@example.com")
    _git(depot, "config", "user.name", "A")
    _git(depot, "config", "commit.gpgsign", "true")
    _git(depot, "config", "gpg.program", script.as_posix())
    (depot / "f.txt").write_text("1", encoding="utf-8")
    subprocess.run(build_command(("add", "f.txt")), cwd=depot, check=True)

    res = subprocess.run(build_command(("commit", "-q", "-m", "x")), cwd=depot, check=False)

    assert res.returncode == 0
    assert not temoin.exists()


class _GitSansCommit(GitWorkspaceDouble):
    async def commit_all(self, message: str) -> str:
        raise AssertionError("the blocking commit must be skipped")


async def test_filter_added_during_the_run_blocks_without_running_it(tmp_path: Path) -> None:
    depot = tmp_path / "depot"
    depot.mkdir()
    temoin = tmp_path / "temoin"
    _git(depot, "init", "-q")
    orch = _Orch(depot)
    orch._git_workspace = _GitSansCommit()

    async def _appel() -> str:
        script = f"echo x > '{temoin.as_posix()}'; cat"
        _git(depot, "config", "filter.x.clean", script)
        (depot / ".gitattributes").write_text("*.txt filter=x\n", encoding="utf-8")
        (depot / "a.txt").write_text("1", encoding="utf-8")
        return "fait"

    arret = await gardee(orch, _run([]), _appel())  # type: ignore[arg-type]

    assert isinstance(arret, PipelineResult)
    assert arret.final_status is TicketStatus.blocked
    assert not temoin.exists()


def test_config_git_changee_recognizes_git_config_names_only() -> None:
    assert config_git_changee([".git/config"])
    assert config_git_changee(["ticket-1/config.worktree"])
    assert not config_git_changee(["agents.json", ".claude/settings.json"])
