"""The common git runner neutralises hooks for every write — ticket-677.

Chaque scénario pose des hooks-pièges qui écrivent un fichier-témoin, puis
passe par un module appelant : le témoin ne doit jamais apparaître.
"""
import inspect
import subprocess
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from pathlib import Path

import pytest

from tessera.services import (
    branch_cleanup,
    git_runner,
    journal_en_attente,
    project_removal,
    realignement_base,
    reprise_orphelin,
    temporary_worktree,
    ticket_diff,
)
from tessera.services.git_runner import GitResult, git, writes
from tessera.services.git_workspace import GitCommandError

#: Hooks qui, ensemble, couvrent un commit, un checkout et toute mise à jour de ref.
_HOOKS = ("pre-commit", "post-checkout", "post-merge", "reference-transaction")
_JOURNAL = Path("memory") / "pipeline-log.md"


def _sync(cwd: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    )
    return done.stdout.strip()


def _init(path: Path) -> Path:
    path.mkdir(parents=True)
    _sync(path, "init", "-q", "-b", "develop")
    _config(path)
    (path / "README.md").write_text("init\n", encoding="utf-8")
    _sync(path, "add", "README.md")
    _sync(path, "commit", "-q", "-m", "init")
    return path


def _config(repo: Path) -> None:
    _sync(repo, "config", "user.email", "t@t.local")
    _sync(repo, "config", "user.name", "t")


def _pieger(repo: Path, tmp_path: Path) -> Path:
    """Install the trap hooks in `repo`; return the witness file they would write."""
    temoin = tmp_path / "temoin.txt"
    for nom in _HOOKS:
        hook = repo / ".git" / "hooks" / nom
        hook.write_text(
            f'#!/bin/sh\necho {nom} >> "{temoin.as_posix()}"\n', encoding="utf-8"
        )
        hook.chmod(0o755)
    temoin.unlink(missing_ok=True)
    return temoin


def test_the_trap_hooks_fire_when_git_runs_plainly(tmp_path: Path) -> None:
    repo = _init(tmp_path / "repo")
    _sync(repo, "branch", "ticket-001-x")
    temoin = _pieger(repo, tmp_path)

    _sync(repo, "commit", "-q", "--allow-empty", "-m", "plain")
    _sync(repo, "checkout", "HEAD", "--", "README.md")
    _sync(repo, "branch", "-D", "ticket-001-x")

    declenches = set(temoin.read_text(encoding="utf-8").split())
    assert {"pre-commit", "post-checkout", "reference-transaction"} <= declenches


async def test_a_write_through_the_runner_runs_no_hook(tmp_path: Path) -> None:
    repo = _init(tmp_path / "repo")
    temoin = _pieger(repo, tmp_path)

    resultat = await git(repo, "commit", "--allow-empty", "-m", "through the runner")

    assert resultat.ok
    assert not temoin.exists()


@pytest.mark.parametrize(
    ("args", "ecrit"),
    [
        (("checkout", "main"), True),
        (("pull", "--ff-only"), True),
        (("commit", "-m", "x"), True),
        (("merge", "x"), True),
        (("rebase", "x"), True),
        (("worktree", "add", "d"), True),
        (("branch", "-D", "x"), True),
        (("diff", "HEAD"), False),
        (("status", "--porcelain"), False),
        (("rev-parse", "HEAD"), False),
        (("log", "-n", "1"), False),
        (("-c", "core.x=1", "status"), False),
        (("-C", "dir", "checkout", "x"), True),
        (("unknown-command",), True),
        ((), True),
    ],
)
def test_writes_is_closed_on_anything_but_a_known_read(
    args: tuple[str, ...], ecrit: bool
) -> None:
    assert writes(args) is ecrit


def test_build_command_adds_the_hooks_path_only_for_a_write() -> None:
    lecture = git_runner.build_command(("status",))
    ecriture = git_runner.build_command(("commit", "-m", "x"))

    assert not any(arg.startswith("core.hooksPath=") for arg in lecture)
    assert any(arg.startswith("core.hooksPath=") for arg in ecriture)
    assert "core.quotePath=false" in lecture


async def test_a_read_does_not_create_the_empty_hooks_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _init(tmp_path / "repo")
    appels: list[str] = []

    def dossier() -> Path:
        appels.append("cree")
        return tmp_path / "vide"

    monkeypatch.setattr(git_runner, "_dossier_sans_hooks", dossier)

    await git(repo, "status", "--porcelain")
    await git(repo, "rev-parse", "HEAD")
    assert appels == []

    await git(repo, "commit", "--allow-empty", "-m", "x")
    assert appels == ["cree"]


async def test_git_returns_code_out_and_err_without_raising(tmp_path: Path) -> None:
    repo = _init(tmp_path / "repo")

    bon = await git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    mauvais = await git(repo, "rev-parse", "--verify", "refs/heads/absente")

    assert isinstance(bon, GitResult)
    assert (bon.code, bon.out.strip(), bon.ok) == (0, "develop", True)
    assert mauvais.code != 0 and not mauvais.ok
    assert mauvais.err


async def test_run_git_returns_stdout_and_raises_on_failure(tmp_path: Path) -> None:
    repo = _init(tmp_path / "repo")

    sortie = await temporary_worktree.run_git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    assert sortie.strip() == "develop"
    with pytest.raises(GitCommandError) as erreur:
        await temporary_worktree.run_git(repo, "rev-parse", "--verify", "refs/heads/absente")
    assert erreur.value.returncode != 0
    assert "rev-parse" in erreur.value.command


# --- un scénario d'écriture par module appelant --------------------------------


async def _scenario_branch_cleanup(tmp_path: Path) -> Path:
    repo = _init(tmp_path / "repo")
    _sync(repo, "branch", "ticket-001-x")
    temoin = _pieger(repo, tmp_path)
    assert await branch_cleanup.supprimer_branches(repo, ["ticket-001-x"]) == ["ticket-001-x"]
    assert "ticket-001-x" not in _sync(repo, "branch", "--format=%(refname:short)")
    return temoin


async def _scenario_journal(tmp_path: Path) -> Path:
    repo = _init(tmp_path / "repo")
    journal = repo / _JOURNAL
    journal.parent.mkdir()
    journal.write_text("une\n", encoding="utf-8")
    _sync(repo, "add", _JOURNAL.as_posix())
    _sync(repo, "commit", "-q", "-m", "journal")
    journal.write_text("une\ndeux\n", encoding="utf-8")
    temoin = _pieger(repo, tmp_path)
    assert await journal_en_attente.mettre_de_cote(repo) == ["deux"]
    assert journal.read_text(encoding="utf-8") == "une\n"
    return temoin


async def _scenario_reprise(tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    repo = _init(workspace / "proj")
    _sync(repo, "checkout", "-q", "-b", "ticket-001-x")
    (repo / "README.md").write_text("modifie\n", encoding="utf-8")
    temoin = _pieger(repo, tmp_path)
    await reprise_orphelin._reprendre_depot_seul(
        "proj", "ticket-001", workspace, datetime(2020, 1, 1, tzinfo=timezone.utc)
    )
    assert _sync(repo, "branch", "--show-current") == "develop"
    assert _sync(repo, "rev-list", "--count", "develop..ticket-001-x") == "1"
    return temoin


async def _scenario_worktree(tmp_path: Path) -> Path:
    repo = _init(tmp_path / "repo")
    temoin = _pieger(repo, tmp_path)
    async with temporary_worktree.detached_worktree(repo, "HEAD") as racine:
        assert (racine / "README.md").is_file()
    return temoin


async def _scenario_realignement(tmp_path: Path) -> Path:
    bare = tmp_path / "bare.git"
    bare.mkdir()
    _sync(bare, "init", "-q", "--bare", "-b", "develop")
    graine = _init(tmp_path / "graine")
    _sync(graine, "remote", "add", "origin", str(bare))
    _sync(graine, "push", "-q", "origin", "develop")
    local = tmp_path / "local"
    _sync(tmp_path, "clone", "-q", str(bare), str(local))
    _config(local)
    (graine / "autre.txt").write_text("x\n", encoding="utf-8")
    _sync(graine, "add", "autre.txt")
    _sync(graine, "commit", "-q", "-m", "avance")
    _sync(graine, "push", "-q", "origin", "develop")
    temoin = _pieger(local, tmp_path)
    assert await realignement_base.realigner_base(local, "develop", "proj") is True
    assert (local / "autre.txt").is_file()
    return temoin


_SCENARIOS: dict[str, Callable[[Path], Awaitable[Path]]] = {
    "branch_cleanup": _scenario_branch_cleanup,
    "journal_en_attente": _scenario_journal,
    "reprise_orphelin": _scenario_reprise,
    "temporary_worktree": _scenario_worktree,
    "realignement_base": _scenario_realignement,
}


@pytest.mark.parametrize("module", sorted(_SCENARIOS))
async def test_every_git_runner_disables_hooks(module: str, tmp_path: Path) -> None:
    temoin = await _SCENARIOS[module](tmp_path)

    assert not temoin.exists(), f"{module}: un hook du dépôt a tourné"


_APPELANTS = (
    branch_cleanup,
    journal_en_attente,
    project_removal,
    realignement_base,
    reprise_orphelin,
    temporary_worktree,
    ticket_diff,
)


@pytest.mark.parametrize("module", _APPELANTS, ids=lambda m: m.__name__.rsplit(".", 1)[-1])
def test_no_caller_spawns_git_itself(module: object) -> None:
    source = inspect.getsource(module)  # type: ignore[arg-type]

    assert "create_subprocess_exec" not in source
    assert "tessera.services.git_runner" in source


async def test_read_only_callers_answer_through_the_common_runner(tmp_path: Path) -> None:
    repo = _init(tmp_path / "repo")

    plan = await branch_cleanup.plan_de_nettoyage(repo)
    plan_retrait = await project_removal.describe_removal(repo)
    diff = await ticket_diff.diff_du_ticket(repo, "ticket-001")

    assert plan.nettoyables == []
    assert plan_retrait.unpushed_commits == 1
    assert diff.diff == ""
