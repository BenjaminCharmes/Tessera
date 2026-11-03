"""A rebase conflict goes to the resolver, or the stop line says why not — ticket-453.

Run on a real git repository: a project whose `agents.json` does not declare
`resolveur-conflit`, conflicting on a code file. The stop line used to be the
same whether the resolver had never been called or had been tried and failed.
"""

import asyncio
import json
from pathlib import Path

import pytest

from tessera.services.git_workspace import GitWorkspaceService
from tessera.services.livraison import Livraison, LivraisonService

_SCHEMA = Path("prisma") / "schema.prisma"


async def _git(cwd: Path, *args: str) -> None:
    proc = await asyncio.create_subprocess_exec(
        "git", *args,
        cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    assert proc.returncode == 0, stderr.decode()


async def _commit(root: Path, contenu: str, message: str) -> None:
    (root / _SCHEMA).write_text(contenu, encoding="utf-8")
    await _git(root, "add", str(_SCHEMA))
    await _git(root, "commit", "-q", "-m", message)


@pytest.fixture
async def repo(tmp_path: Path) -> Path:
    """A project that declares only an autonomy level, in conflict with `main`."""
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
    def __init__(self) -> None:
        self.ouvertures = 0

    async def open_pull_request(self, **kwargs: object) -> object:
        self.ouvertures += 1
        raise AssertionError("un conflit non résolu n'ouvre aucune PR")


async def _livrer(root: Path, resolveur: object | None) -> tuple[Livraison, _Workflow]:
    workflow = _Workflow()
    service = LivraisonService(
        git_workspace=GitWorkspaceService(root),
        workflow=workflow,  # type: ignore[arg-type]
        project_path=root,
        base_branch="main",
        resolveur=resolveur,  # type: ignore[arg-type]
    )
    livraison = await service.livrer_phase_1(
        ticket_id="ticket-005",
        ticket_title="T",
        ticket_body="",
        branch="ticket-005-x",
        approuve=True,
    )
    return livraison, workflow


async def test_a_conflict_with_a_resolver_calls_it_and_says_it_failed(
    repo: Path,
) -> None:
    appels: list[tuple[str, ...]] = []

    async def resoudre(fichiers: tuple[str, ...]) -> None:
        appels.append(fichiers)
        (repo / _SCHEMA).write_text("<<<<<<< HEAD\nmodel A\n", encoding="utf-8")

    livraison, workflow = await _livrer(repo, resoudre)

    assert appels == [("prisma/schema.prisma",)]
    assert workflow.ouvertures == 0
    assert livraison.conflits == ("prisma/schema.prisma",)
    assert "résolveur tenté" in (livraison.arret or "")
    assert "marqueurs de conflit restants" in (livraison.arret or "")
    assert any(e.startswith("résolveur tenté") for e in livraison.etapes)
    assert len(livraison.etapes) == len(livraison.durees_ms)


async def test_a_resolver_that_raises_names_its_error_in_the_stop_line(
    repo: Path,
) -> None:
    async def resoudre(fichiers: tuple[str, ...]) -> None:
        raise RuntimeError("abandon")

    livraison, _workflow = await _livrer(repo, resoudre)

    assert "résolveur tenté" in (livraison.arret or "")
    assert "RuntimeError" in (livraison.arret or "")


async def test_a_conflict_without_a_resolver_says_it_was_not_tried(
    repo: Path,
) -> None:
    livraison, workflow = await _livrer(repo, None)

    assert workflow.ouvertures == 0
    assert livraison.conflits == ("prisma/schema.prisma",)
    assert "résolveur non tenté" in (livraison.arret or "")
    assert not any(e.startswith("résolveur tenté") for e in livraison.etapes)


async def test_the_reason_is_set_when_a_file_goes_missing(repo: Path) -> None:
    service = GitWorkspaceService(repo)

    async def resoudre(fichiers: tuple[str, ...]) -> None:
        (repo / _SCHEMA).unlink()

    conflits = await service.rejouer_sur("main", resolveur=resoudre)

    assert conflits == ("prisma/schema.prisma",)
    assert "introuvable" in (service.raison_resolveur or "")


async def test_the_reason_is_cleared_when_the_resolver_succeeds(repo: Path) -> None:
    service = GitWorkspaceService(repo)
    service.raison_resolveur = "reste d'une tentative précédente"

    async def resoudre(fichiers: tuple[str, ...]) -> None:
        (repo / _SCHEMA).write_text("model A { les deux }\n", encoding="utf-8")

    conflits = await service.rejouer_sur("main", resolveur=resoudre)

    assert conflits == ()
    assert service.raison_resolveur is None
