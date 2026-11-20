"""Log lines written outside a run wait outside the tree — tickets 786 and 789.

Une file interrompue, ou `CIWatcher` après un merge, écrit dans le journal alors
que le checkout est sur la base : l'arbre doit rester propre. Les lignes
attendent hors du suivi git, et le run suivant les réécrit dans sa branche.
"""
import asyncio
from pathlib import Path
from typing import Any

from tessera.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from tessera.services.git_workspace import GitWorkspaceService, journal_attente
from tessera.services.noyau.pipeline_events import OrchestratorEvent
from tessera.services.pipeline import pipeline_branche
from tessera.services.pipeline.pipeline_fin_de_file import nettoyer_apres_file
from tessera.services.pipeline.pipeline_run import PipelineRun

_LOG = Path("memory") / "pipeline-log.md"
_LIGNE = "- 2026-11-04 10:00:00 UTC — [portfolio] file interrompue : ticket-021 n'a pas été livré"


async def _git(cwd: Path, *args: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        "git", *args, cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    assert proc.returncode == 0, stderr.decode()
    return stdout.decode().strip()


async def _depot(root: Path, suivi: bool = True) -> None:
    root.mkdir()
    await _git(root, "init", "-q", "-b", "main")
    await _git(root, "config", "user.email", "test@tessera.local")
    await _git(root, "config", "user.name", "Tessera test")
    (root / "memory").mkdir()
    (root / _LOG).write_text("# log\n", encoding="utf-8")
    (root / "code.py").write_text("x = 1\n", encoding="utf-8")
    if suivi:
        await _git(root, "add", ".")
    else:
        await _git(root, "add", "code.py")
    await _git(root, "commit", "-q", "-m", "init")


def _ecrire(root: Path, ligne: str) -> None:
    with (root / _LOG).open("a", encoding="utf-8") as f:
        f.write(ligne + "\n")


class _Orch:
    def __init__(self, workspace: GitWorkspaceService, racine: Path) -> None:
        self._git_workspace = workspace
        self._project_path = racine
        self._base_branch = "main"
        self.logs: list[str] = []

    def _log(self, message: str) -> None:
        self.logs.append(message)

    async def _ticket_status(self, *args: Any) -> None:
        return None


class _Tickets:
    async def update_status(self, ticket_id: str, status: TicketStatus) -> None:
        return None


def _run() -> PipelineRun:
    async def _on_event(event: OrchestratorEvent) -> None:
        pass

    ticket = Ticket(
        id="ticket-022", title="Next feature", type=TicketType.feat,
        status=TicketStatus.todo, priority=TicketPriority.medium,
        agent="codeur", body="",
    )
    return PipelineRun(project_id="projet", ticket=ticket, on_event=_on_event)


async def _attente(root: Path) -> Path:
    commun = await _git(root, "rev-parse", "--git-common-dir")
    return (root / commun).resolve() / "tessera-pipeline-log-attente"


async def test_queue_close_leaves_the_base_clean_and_keeps_the_line(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    await _depot(root)
    _ecrire(root, _LIGNE)  # écrite par `_interrompre`, la livraison est déjà revenue sur la base
    assert await _git(root, "status", "--porcelain") != ""

    await nettoyer_apres_file(_Orch(GitWorkspaceService(root), root))  # type: ignore[arg-type]

    assert await _git(root, "status", "--porcelain") == ""
    assert (await _attente(root)).read_text(encoding="utf-8") == _LIGNE + "\n"


async def test_the_queued_line_reaches_the_next_run_branch_and_the_file_is_emptied(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    await _depot(root)
    _ecrire(root, _LIGNE)
    orch = _Orch(GitWorkspaceService(root), root)
    await nettoyer_apres_file(orch)  # type: ignore[arg-type]
    orch._ticket_svc = _Tickets()  # type: ignore[attr-defined]

    run = _run()
    assert await pipeline_branche.create_branch(orch, run) is None  # type: ignore[arg-type]

    assert run.branch is not None
    assert await _git(root, "branch", "--show-current") == run.branch
    assert _LIGNE in (root / _LOG).read_text(encoding="utf-8")
    assert not (await _attente(root)).exists()
    # Le journal de la branche porte la ligne, que la tenue de livres du run commitera.
    assert await _git(root, "status", "--porcelain") == "M memory/pipeline-log.md"


async def test_an_untracked_log_is_neither_set_aside_nor_restored(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    await _depot(root, suivi=False)
    _ecrire(root, _LIGNE)

    await nettoyer_apres_file(_Orch(GitWorkspaceService(root), root))  # type: ignore[arg-type]

    assert _LIGNE in (root / _LOG).read_text(encoding="utf-8")
    assert not (await _attente(root)).exists()


async def test_ranger_apres_file_without_a_modified_log_writes_nothing(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    await _depot(root)

    await journal_attente.ranger_apres_file(root)

    assert not (await _attente(root)).exists()


async def test_mettre_en_attente_then_reprendre_returns_the_lines_once(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    await _depot(root)

    assert await journal_attente.mettre_en_attente(root, ["- a", "- b"])
    assert await journal_attente.mettre_en_attente(root, ["- c"])

    assert await journal_attente.reprendre(root) == ["- a", "- b", "- c"]
    assert await journal_attente.reprendre(root) == []


def test_a_path_that_is_not_a_pipeline_log_is_not_queued(tmp_path: Path) -> None:
    ailleurs = tmp_path / "notes.md"

    assert journal_attente.racine_du_journal(ailleurs) is None
    assert journal_attente.attente_vers_fichier(ailleurs, "- x") is False


async def test_a_worktree_run_rewrites_the_queued_lines_in_its_own_log(tmp_path: Path) -> None:
    from tessera.services.pipeline.run_dans_worktree import _reprendre_les_lignes_en_attente

    root = tmp_path / "repo"
    await _depot(root)
    await journal_attente.mettre_en_attente(root, [_LIGNE])
    wt = tmp_path / "wt"
    await _git(root, "worktree", "add", "-q", "-b", "ticket-022-x", str(wt))

    class _OrchWt:
        _log_path = wt / _LOG

    await _reprendre_les_lignes_en_attente(_OrchWt())  # type: ignore[arg-type]

    assert _LIGNE in (wt / _LOG).read_text(encoding="utf-8")
    assert not (await _attente(root)).exists()
