"""A conflict handed to the resolver is announced — ticket-559.

Run on a real git repository, like `test_resolveur_non_tente.py`: `started`
carries the files, `ended` carries what the rebase ruled.
"""
import asyncio
import json
from pathlib import Path

import pytest

from tessera.services.git_workspace import GitWorkspaceService
from tessera.services.livraison import LivraisonService
from tessera.services.livraison_conflit import signal_courant
from tessera.services.livraison_evenements import evenements_de_livraison
from tessera.services.pipeline_events import EventType, OrchestratorEvent

_SCHEMA = Path("prisma") / "schema.prisma"


async def _git(cwd: Path, *args: str) -> None:
    proc = await asyncio.create_subprocess_exec(
        "git", *args, cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    assert proc.returncode == 0, stderr.decode()


async def _commit(root: Path, contenu: str, message: str) -> None:
    (root / _SCHEMA).write_text(contenu, encoding="utf-8")
    await _git(root, "add", str(_SCHEMA))
    await _git(root, "commit", "-q", "-m", message)


@pytest.fixture
async def repo(tmp_path: Path) -> Path:
    root = tmp_path / "projet"
    (root / "prisma").mkdir(parents=True)
    await _git(root, "init", "-q", "-b", "main")
    await _git(root, "config", "user.email", "test@tessera.local")
    await _git(root, "config", "user.name", "Tessera test")
    (root / "agents.json").write_text(json.dumps({"autonomy": "pr"}), encoding="utf-8")
    await _git(root, "add", "agents.json")
    await _commit(root, "model A {}\n", "init")
    await _git(root, "checkout", "-q", "-b", "ticket-005-x")
    await _commit(root, "model A { branche }\n", "feat: branche")
    await _git(root, "checkout", "-q", "main")
    await _commit(root, "model A { base }\n", "chore: base")
    await _git(root, "checkout", "-q", "ticket-005-x")
    return root


class _Workflow:
    async def open_pull_request(self, **kwargs: object) -> object:
        raise AssertionError("ces tests n'atteignent pas l'ouverture de la PR")


async def _livrer_avec_resolveur(root: Path, ecrit: str) -> list[OrchestratorEvent]:
    recus: list[OrchestratorEvent] = []

    async def on_event(event: OrchestratorEvent) -> None:
        recus.append(event)

    async def resoudre(fichiers: tuple[str, ...]) -> None:
        (root / _SCHEMA).write_text(ecrit, encoding="utf-8")

    service = LivraisonService(
        git_workspace=GitWorkspaceService(root),
        workflow=_Workflow(),  # type: ignore[arg-type]
        project_path=root,
        base_branch="main",
        resolveur=resoudre,
    )
    with evenements_de_livraison(on_event, "ticket-005"):
        try:
            await service.livrer_phase_1(
                ticket_id="ticket-005", ticket_title="T", ticket_body="",
                branch="ticket-005-x", approuve=True,
            )
        except AssertionError:
            pass  # le rebase a abouti : seule l'ouverture de la PR n'est pas simulée
    return recus


def _conflits(recus: list[OrchestratorEvent]) -> list[dict[str, object]]:
    return [e.data for e in recus if e.type is EventType.CONFLICT_RESOLUTION]


async def test_a_resolved_conflict_announces_started_then_ended_resolved(repo: Path) -> None:
    recus = await _livrer_avec_resolveur(repo, "model A { les deux }\n")

    assert _conflits(recus) == [
        {"phase": "started", "files": ["prisma/schema.prisma"], "outcome": None},
        {"phase": "ended", "files": ["prisma/schema.prisma"], "outcome": "resolved"},
    ]


async def test_a_cancelled_conflict_announces_started_then_ended_cancelled(repo: Path) -> None:
    recus = await _livrer_avec_resolveur(repo, "<<<<<<< HEAD\nmodel A\n")

    assert _conflits(recus) == [
        {"phase": "started", "files": ["prisma/schema.prisma"], "outcome": None},
        {"phase": "ended", "files": ["prisma/schema.prisma"], "outcome": "cancelled"},
    ]


async def test_outside_a_run_there_is_no_conflict_announcer() -> None:
    assert signal_courant() is None
