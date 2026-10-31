"""A run starts from the realigned base, with no manual step — ticket-457.

Real git repositories: the failure lived in the interplay of checkout, fast
forward and the pending pipeline-log lines, which a double cannot reproduce.
"""
import asyncio
from pathlib import Path

import pytest

from tessera.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from tessera.services import pipeline_branche
from tessera.services.git_workspace import GitWorkspaceService
from tessera.services.pipeline_events import OrchestratorEvent
from tessera.services.pipeline_run import PipelineRun

_JOURNAL = "memory/pipeline-log.md"
_LIGNE_DEJA_SUR_LA_BASE = "- 2026-10-15 09:00:00 UTC — [ticket-001] PR #1 mergée"
_LIGNE_EN_ATTENTE = "- 2026-10-15 09:01:00 UTC — [ticket-001] confiée au CIWatcher"


async def _git(cwd: Path, *args: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        "git", *args,
        cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    assert proc.returncode == 0, err.decode()
    return out.decode().strip()


class _TicketSvc:
    def __init__(self) -> None:
        self.statuts: list[TicketStatus] = []

    async def update_status(self, ticket_id: str, status: TicketStatus) -> None:
        self.statuts.append(status)


class _Orch:
    """Orchestrator stand-in holding what the start stages read."""

    def __init__(self, workspace: GitWorkspaceService, racine: Path) -> None:
        self._git_workspace = workspace
        self._project_path = racine
        self._base_branch = "develop"
        self._ticket_svc = _TicketSvc()
        self.logs: list[str] = []

    async def _sur_la_base(self) -> bool:
        return await self._git_workspace.branche_courante() == self._base_branch

    def _log(self, message: str) -> None:
        self.logs.append(message)


def _run() -> PipelineRun:
    async def _on_event(event: OrchestratorEvent) -> None:
        pass

    ticket = Ticket(
        id="ticket-002", title="Suite", type=TicketType.feat,
        status=TicketStatus.todo, priority=TicketPriority.medium,
        agent="codeur", body="",
    )
    return PipelineRun(project_id="projet", ticket=ticket, on_event=_on_event)


@pytest.fixture
async def arbre_reste_sur_un_ticket(tmp_path: Path) -> tuple[Path, str]:
    """Tree left on the previous ticket's branch, remote one merge ahead.

    The log holds two uncommitted lines; the remote merge already carries one
    of them. Returns the local repository and the remote tip.
    """
    bare = tmp_path / "remote.git"
    bare.mkdir()
    await _git(bare, "init", "--bare", "-q")
    local = tmp_path / "local"
    local.mkdir()
    await _git(local, "init", "-q")
    await _git(local, "config", "user.email", "test@tessera.local")
    await _git(local, "config", "user.name", "Tessera test")
    (local / "README.md").write_text("# projet\n", encoding="utf-8")
    (local / "memory").mkdir()
    (local / _JOURNAL).write_text("- ligne 1\n", encoding="utf-8")
    await _git(local, "add", "README.md", _JOURNAL)
    await _git(local, "commit", "-q", "-m", "init")
    await _git(local, "branch", "-M", "develop")
    await _git(local, "remote", "add", "origin", str(bare))
    await _git(local, "push", "-q", "--set-upstream", "origin", "develop")

    await _git(local, "checkout", "-q", "-b", "ticket-001-ancien")
    (local / "a.py").write_text("x = 1\n", encoding="utf-8")
    await _git(local, "add", "a.py")
    await _git(local, "commit", "-q", "-m", "feat: ticket-001")

    # Le merge de ce ticket, côté distant, avec sa ligne de journal.
    autre = tmp_path / "autre"
    await _git(tmp_path, "clone", "-q", "-b", "develop", str(bare), str(autre))
    await _git(autre, "config", "user.email", "test@tessera.local")
    await _git(autre, "config", "user.name", "Tessera test")
    (autre / "a.py").write_text("x = 1\n", encoding="utf-8")
    with (autre / _JOURNAL).open("a", encoding="utf-8") as f:
        f.write(_LIGNE_DEJA_SUR_LA_BASE + "\n")
    await _git(autre, "add", "a.py", _JOURNAL)
    await _git(autre, "commit", "-q", "-m", "feat: ticket-001 (#1)")
    await _git(autre, "push", "-q", "origin", "develop")
    distant = await _git(autre, "rev-parse", "HEAD")

    with (local / _JOURNAL).open("a", encoding="utf-8") as f:
        f.write(_LIGNE_DEJA_SUR_LA_BASE + "\n" + _LIGNE_EN_ATTENTE + "\n")
    return local, distant


async def test_le_run_demarre_sur_la_base_realignee_depuis_une_branche_de_ticket(
    arbre_reste_sur_un_ticket: tuple[Path, str],
) -> None:
    local, distant = arbre_reste_sur_un_ticket
    run = _run()

    refused = await pipeline_branche.create_branch(
        _Orch(GitWorkspaceService(local), local), run  # type: ignore[arg-type]
    )

    assert refused is None
    assert run.branch is not None
    assert await _git(local, "branch", "--show-current") == run.branch
    assert await _git(local, "rev-parse", "HEAD") == distant
    # La base locale a suivi le distant sans commit local : elle ne diverge pas.
    assert await _git(local, "rev-parse", "develop") == distant


async def test_les_lignes_du_journal_survivent_une_seule_fois_chacune(
    arbre_reste_sur_un_ticket: tuple[Path, str],
) -> None:
    local, _distant = arbre_reste_sur_un_ticket

    await pipeline_branche.create_branch(
        _Orch(GitWorkspaceService(local), local), _run()  # type: ignore[arg-type]
    )

    lignes = (local / _JOURNAL).read_text(encoding="utf-8").splitlines()
    assert lignes.count(_LIGNE_DEJA_SUR_LA_BASE) == 1
    assert lignes.count(_LIGNE_EN_ATTENTE) == 1
    assert lignes.count("- ligne 1") == 1


async def test_un_autre_fichier_modifie_bloque_toujours_le_depart(
    arbre_reste_sur_un_ticket: tuple[Path, str],
) -> None:
    local, _distant = arbre_reste_sur_un_ticket
    (local / "README.md").write_text("# modifié à la main\n", encoding="utf-8")
    avant = await _git(local, "rev-parse", "HEAD")
    orch = _Orch(GitWorkspaceService(local), local)

    result = await pipeline_branche.ensure_clean_tree(orch, _run())  # type: ignore[arg-type]

    assert result is not None
    assert result.final_status is TicketStatus.blocked
    assert orch._ticket_svc.statuts == [TicketStatus.blocked]
    assert await _git(local, "branch", "--show-current") == "ticket-001-ancien"
    assert await _git(local, "rev-parse", "HEAD") == avant
