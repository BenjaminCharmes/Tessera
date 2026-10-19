"""A delivery rebase keeps both sides of an additive Prisma conflict — ticket-484."""
import asyncio
from pathlib import Path

import pytest

from tessera.services.git_workspace import GitWorkspaceService

_SCHEMA = "prisma/schema.prisma"
_ANCETRE = "model User {\n  id Int @id\n}\n"
_ORDER = "model Order {\n  id Int @id\n}\n"
_WISH = "model Wish {\n  id Int @id\n}\n"


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


@pytest.fixture
async def repo(tmp_path: Path) -> Path:
    root = tmp_path / "projet"
    (root / "prisma").mkdir(parents=True)
    await _git(root, "init", "-q")
    await _git(root, "config", "user.email", "test@tessera.local")
    await _git(root, "config", "user.name", "Tessera test")
    (root / _SCHEMA).write_text(_ANCETRE, encoding="utf-8")
    await _git(root, "add", ".")
    await _git(root, "commit", "-q", "-m", "init")
    return root


async def _diverger(repo: Path, version_ticket: str, version_base: str) -> str:
    """A ticket branch and an advanced base that both rewrite the schema."""
    base = await _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    await _git(repo, "checkout", "-q", "-b", "ticket-009-schema")
    (repo / _SCHEMA).write_text(version_ticket, encoding="utf-8")
    await _git(repo, "commit", "-q", "-am", "feat: ticket-009")
    await _git(repo, "checkout", "-q", base)
    (repo / _SCHEMA).write_text(version_base, encoding="utf-8")
    await _git(repo, "commit", "-q", "-am", "feat: ticket-008")
    await _git(repo, "checkout", "-q", "ticket-009-schema")
    return base


async def test_two_models_added_to_the_schema_are_both_kept(repo: Path) -> None:
    base = await _diverger(repo, _ANCETRE + "\n" + _WISH, _ANCETRE + "\n" + _ORDER)
    appels: list[tuple[str, ...]] = []

    async def resolveur(fichiers: tuple[str, ...]) -> None:
        appels.append(fichiers)

    conflits = await GitWorkspaceService(repo).rejouer_sur(base, resolveur=resolveur)

    assert conflits == ()
    assert appels == [], "the resolver agent is not called for a pure addition"
    schema = (repo / _SCHEMA).read_text(encoding="utf-8")
    assert "model Order {" in schema and "model Wish {" in schema
    assert "<<<<<<<" not in schema and ">>>>>>>" not in schema
    assert schema.count("{") == schema.count("}")
    assert await _git(repo, "status", "--porcelain") == ""
    assert not (repo / ".git" / "rebase-merge").exists()


async def test_additive_conflict_resolves_without_any_resolver(repo: Path) -> None:
    base = await _diverger(repo, _ANCETRE + "\n" + _WISH, _ANCETRE + "\n" + _ORDER)

    conflits = await GitWorkspaceService(repo).rejouer_sur(base)

    assert conflits == ()
    assert "model Wish {" in (repo / _SCHEMA).read_text(encoding="utf-8")


async def test_a_conflict_that_edits_an_existing_model_still_reaches_the_resolver(
    repo: Path,
) -> None:
    edite = "model User {\n  id Int @id\n  name String\n}\n"
    autre = "model User {\n  id Int @id\n  email String\n}\n"
    base = await _diverger(repo, edite, autre + "\n" + _ORDER)
    avant = await _git(repo, "rev-parse", "HEAD")
    appels: list[tuple[str, ...]] = []

    async def resolveur(fichiers: tuple[str, ...]) -> None:
        appels.append(fichiers)

    service = GitWorkspaceService(repo)
    conflits = await service.rejouer_sur(base, resolveur=resolveur)

    assert appels == [(_SCHEMA,)]
    assert conflits == (_SCHEMA,)
    # Le résolveur n'a rien écrit : tout est annulé, la branche est intacte.
    assert await _git(repo, "rev-parse", "HEAD") == avant
    assert await service.is_clean()


async def test_mixed_conflict_with_a_non_prisma_file_goes_to_the_resolver(
    repo: Path,
) -> None:
    (repo / "README.md").write_text("v0\n", encoding="utf-8")
    await _git(repo, "add", ".")
    await _git(repo, "commit", "-q", "-m", "docs: readme")
    base = await _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    await _git(repo, "checkout", "-q", "-b", "ticket-009-mixte")
    (repo / "README.md").write_text("ticket\n", encoding="utf-8")
    (repo / _SCHEMA).write_text(_ANCETRE + "\n" + _WISH, encoding="utf-8")
    await _git(repo, "commit", "-q", "-am", "feat: ticket-009")
    await _git(repo, "checkout", "-q", base)
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    (repo / _SCHEMA).write_text(_ANCETRE + "\n" + _ORDER, encoding="utf-8")
    await _git(repo, "commit", "-q", "-am", "feat: ticket-008")
    await _git(repo, "checkout", "-q", "ticket-009-mixte")
    appels: list[tuple[str, ...]] = []

    async def resolveur(fichiers: tuple[str, ...]) -> None:
        appels.append(fichiers)

    conflits = await GitWorkspaceService(repo).rejouer_sur(base, resolveur=resolveur)

    assert appels == [("README.md", _SCHEMA)]
    assert conflits == ("README.md", _SCHEMA)


async def test_additive_conflict_resolves_in_a_project_nested_in_its_repository(
    tmp_path: Path,
) -> None:
    depot = tmp_path / "depot"
    projet = depot / "projects" / "p"
    (projet / "prisma").mkdir(parents=True)
    await _git(depot, "init", "-q")
    await _git(depot, "config", "user.email", "test@tessera.local")
    await _git(depot, "config", "user.name", "Tessera test")
    (projet / "agents.json").write_text('{"git_root": "ancestor"}\n', encoding="utf-8")
    (projet / _SCHEMA).write_text(_ANCETRE, encoding="utf-8")
    await _git(depot, "add", ".")
    await _git(depot, "commit", "-q", "-m", "init")
    base = await _diverger(projet, _ANCETRE + "\n" + _WISH, _ANCETRE + "\n" + _ORDER)

    conflits = await GitWorkspaceService(projet).rejouer_sur(base)

    assert conflits == ()
    schema = (projet / _SCHEMA).read_text(encoding="utf-8")
    assert "model Order {" in schema and "model Wish {" in schema
    assert await _git(depot, "status", "--porcelain") == ""
