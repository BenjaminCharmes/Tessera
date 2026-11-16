"""A stale local ticket is replaced by the remote one before any agent — ticket-977.

Real git repositories and a real `TicketService`: the failure lived in the
fast-forward of the base, which a mocked `get_ticket` cannot reproduce.
"""
import asyncio
from pathlib import Path
from unittest.mock import MagicMock

from tessera.services.agents.agent_runner import AgentRunner
from tessera.services.git_workspace import GitWorkspaceService
from tessera.services.noyau.pipeline_events import EventType, OrchestratorEvent
from tessera.services.pipeline.pipeline_run import PipelineRun
from tessera.services.pipeline.ticket_apres_avance import creer_branche_et_relire
from tessera.services.projets.ticket_service import TicketService

_FICHE = "tickets/todo/ticket-100-compteur.md"


def _texte(corps: str, preuve: bool) -> str:
    return (
        "---\nagent: codeur\ncreated: 2026-11-14\ndepends_on: []\nid: ticket-100\n"
        f"pr_number: null\npreuve_reelle: {str(preuve).lower()}\npriority: high\n"
        "status: todo\ntitle: Compteur\ntype: feat\n---\n\n" + corps + "\n"
    )


async def _git(cwd: Path, *args: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        "git", *args, cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    assert proc.returncode == 0, err.decode()
    return out.decode().strip()


async def _identite(depot: Path) -> None:
    await _git(depot, "config", "user.email", "test@tessera.local")
    await _git(depot, "config", "user.name", "Tessera test")


async def _depot_perime(tmp_path: Path) -> Path:
    """Local base on version A of the ticket, `origin/develop` on version B."""
    bare = tmp_path / "remote.git"
    bare.mkdir()
    await _git(bare, "init", "--bare", "-q")
    local = tmp_path / "local"
    local.mkdir()
    await _git(local, "init", "-q")
    await _identite(local)
    (local / "tickets/todo").mkdir(parents=True)
    (local / _FICHE).write_text(_texte("Compter par pseudo seul.", False), encoding="utf-8")
    await _git(local, "add", _FICHE)
    await _git(local, "commit", "-q", "-m", "init")
    await _git(local, "branch", "-M", "develop")
    await _git(local, "remote", "add", "origin", str(bare))
    await _git(local, "push", "-q", "--set-upstream", "origin", "develop")

    autre = tmp_path / "autre"
    await _git(tmp_path, "clone", "-q", "-b", "develop", str(bare), str(autre))
    await _identite(autre)
    (autre / _FICHE).write_text(_texte("Compter par couple pseudo et appareil.", True), encoding="utf-8")
    await _git(autre, "add", _FICHE)
    await _git(autre, "commit", "-q", "-m", "docs: rewrite ticket-100")
    await _git(autre, "push", "-q", "origin", "develop")
    return local


class _Orch:
    def __init__(self, racine: Path) -> None:
        self._git_workspace = GitWorkspaceService(racine)
        self._project_path = racine
        self._base_branch = "develop"
        self._ticket_svc = TicketService(racine, "projet")
        self._preuves_reelles: dict[str, bool] = {}
        self.logs: list[str] = []

    def _log(self, message: str) -> None:
        self.logs.append(message)


async def test_run_reads_remote_version_and_coder_prompt_carries_it(tmp_path: Path) -> None:
    local = await _depot_perime(tmp_path)
    orch = _Orch(local)
    ancienne = await orch._ticket_svc.get_ticket("ticket-100")
    assert ancienne is not None and "pseudo seul" in ancienne.body
    orch._preuves_reelles["ticket-100"] = False
    evenements: list[OrchestratorEvent] = []

    async def on_event(e: OrchestratorEvent) -> None:
        evenements.append(e)

    run = PipelineRun(project_id="projet", ticket=ancienne, on_event=on_event)

    refus = await creer_branche_et_relire(orch, run)  # type: ignore[arg-type]

    assert refus is None
    assert "couple pseudo et appareil" in run.ticket.body
    assert orch._preuves_reelles["ticket-100"] is True
    relus = [e for e in evenements if e.type == EventType.TICKET_RELU_APRES_AVANCE]
    assert len(relus) == 1
    assert relus[0].data["nouveau_sha"] == await _git(local, "rev-parse", "develop")
    assert relus[0].data["ancien_sha"] != relus[0].data["nouveau_sha"]
    assert len(orch.logs) >= 1 and any("fiche relue" in ligne for ligne in orch.logs)
    prompt = AgentRunner._build_user_prompt(MagicMock(), run.ticket, "codeur", "")
    assert "couple pseudo et appareil" in prompt
    assert "pseudo seul" not in prompt


async def test_unchanged_ticket_on_a_real_repo_emits_nothing(tmp_path: Path) -> None:
    local = await _depot_perime(tmp_path)
    await _git(local, "pull", "-q", "--ff-only", "origin", "develop")
    orch = _Orch(local)
    ticket = await orch._ticket_svc.get_ticket("ticket-100")
    assert ticket is not None
    evenements: list[OrchestratorEvent] = []

    async def on_event(e: OrchestratorEvent) -> None:
        evenements.append(e)

    run = PipelineRun(project_id="projet", ticket=ticket, on_event=on_event)

    assert await creer_branche_et_relire(orch, run) is None  # type: ignore[arg-type]

    assert [e for e in evenements if e.type == EventType.TICKET_RELU_APRES_AVANCE] == []
    assert not any("fiche relue" in ligne for ligne in orch.logs)

