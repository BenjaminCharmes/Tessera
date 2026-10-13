"""Append-only pipeline files never stop a delivery rebase — ticket-418."""
import asyncio
import json
from pathlib import Path

import pytest

from tessera.services.git_attributes import declare_union_merge, union_attribute_line
from tessera.services.git_workspace import GitWorkspaceService, _union_json_lists

_LIGNE = "memory/pipeline-log.md merge=union"


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
    root.mkdir()
    await _git(root, "init", "-q")
    await _git(root, "config", "user.email", "test@tessera.local")
    await _git(root, "config", "user.name", "Tessera test")
    (root / "memory").mkdir()
    (root / "memory" / "pipeline-log.md").write_text("# log\n", encoding="utf-8")
    (root / "memory" / "documentation.json").write_text(
        '{"documentes": []}\n', encoding="utf-8"
    )
    (root / "README.md").write_text("v0\n", encoding="utf-8")
    await _git(root, "add", ".")
    await _git(root, "commit", "-q", "-m", "init")
    return root


def _attributs(repo: Path) -> list[str]:
    fichier = repo / ".git" / "info" / "attributes"
    return fichier.read_text(encoding="utf-8").splitlines() if fichier.is_file() else []


# --- declaration ------------------------------------------------------------


async def test_create_branch_declares_union_merge_without_duplicate(repo: Path) -> None:
    service = GitWorkspaceService(repo)

    await service.create_branch("ticket-001", "first")
    await service.create_branch("ticket-002", "second")
    await GitWorkspaceService(repo).create_branch("ticket-003", "third")

    assert _attributs(repo).count(_LIGNE) == 1
    # Rien dans le dépôt versionné : seul `.git/info/attributes` est touché.
    assert not (repo / ".gitattributes").exists()


async def test_declaration_carries_project_prefix_when_nested(tmp_path: Path) -> None:
    root = tmp_path / "depot"
    projet = root / "projects" / "p"
    projet.mkdir(parents=True)
    await _git(root, "init", "-q")
    await _git(root, "config", "user.email", "test@tessera.local")
    await _git(root, "config", "user.name", "Tessera test")
    (projet / "agents.json").write_text('{"git_root": "ancestor"}\n', encoding="utf-8")
    await _git(root, "add", ".")
    await _git(root, "commit", "-q", "-m", "init")

    await GitWorkspaceService(projet).create_branch("ticket-001", "nested")

    assert f"projects/p/{_LIGNE}" in _attributs(root)


def test_declare_union_merge_keeps_user_lines_and_adds_missing_newline(
    tmp_path: Path,
) -> None:
    fichier = tmp_path / "info" / "attributes"
    fichier.parent.mkdir()
    fichier.write_text("*.bin binary", encoding="utf-8")

    assert declare_union_merge(fichier, "memory/pipeline-log.md") is True
    assert declare_union_merge(fichier, "memory/pipeline-log.md") is False

    assert fichier.read_text(encoding="utf-8").splitlines() == [
        "*.bin binary",
        union_attribute_line("memory/pipeline-log.md"),
    ]


# --- rebase of the journal --------------------------------------------------


async def _brancher_journal(repo: Path) -> tuple[GitWorkspaceService, str, str]:
    """A ticket branch and an advanced base, each appending its own log line."""
    service = GitWorkspaceService(repo)
    base = await _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    branche = await service.create_branch("ticket-009", "journal")
    log = repo / "memory" / "pipeline-log.md"
    log.write_text("# log\n- ticket-009\n", encoding="utf-8")
    await _git(repo, "commit", "-q", "-am", "feat: ticket-009")
    await _git(repo, "checkout", "-q", base)
    log.write_text("# log\n- ticket-008\n", encoding="utf-8")
    await _git(repo, "commit", "-q", "-am", "chore: ticket-008 log")
    await _git(repo, "checkout", "-q", branche)
    return service, base, branche


async def test_git_rebase_keeps_both_journal_lines_natively(repo: Path) -> None:
    """The union driver alone settles it: plain `git rebase`, no Tessera resolver."""
    _, base, _ = await _brancher_journal(repo)

    await _git(repo, "rebase", base)

    contenu = (repo / "memory" / "pipeline-log.md").read_text(encoding="utf-8")
    assert "- ticket-008" in contenu
    assert "- ticket-009" in contenu


async def test_delivery_rebase_keeps_both_journal_lines(repo: Path) -> None:
    service, base, _ = await _brancher_journal(repo)

    conflits = await service.rejouer_sur(base)

    assert conflits == ()
    contenu = (repo / "memory" / "pipeline-log.md").read_text(encoding="utf-8")
    assert "- ticket-008" in contenu
    assert "- ticket-009" in contenu


# --- documentation.json ----------------------------------------------------


async def _brancher_fichier(
    repo: Path, chemin: str, version_branche: str, version_base: str
) -> tuple[GitWorkspaceService, str, str]:
    service = GitWorkspaceService(repo)
    base = await _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    branche = await service.create_branch("ticket-009", "fichier")
    (repo / chemin).write_text(version_branche, encoding="utf-8")
    await _git(repo, "commit", "-q", "-am", "feat: ticket-009")
    await _git(repo, "checkout", "-q", base)
    (repo / chemin).write_text(version_base, encoding="utf-8")
    await _git(repo, "commit", "-q", "-am", "chore: base moves")
    await _git(repo, "checkout", "-q", branche)
    return service, base, branche


async def test_documentation_json_only_conflict_resolves_by_union_of_ids(
    repo: Path,
) -> None:
    service, base, _ = await _brancher_fichier(
        repo,
        "memory/documentation.json",
        json.dumps({"documentes": ["ticket-009"]}),
        json.dumps({"documentes": ["ticket-008"]}),
    )

    conflits = await service.rejouer_sur(base)

    assert conflits == ()
    texte = (repo / "memory" / "documentation.json").read_text(encoding="utf-8")
    assert json.loads(texte) == {"documentes": ["ticket-008", "ticket-009"]}
    assert await service.is_clean()
    assert await _git(repo, "status", "--porcelain") == ""


async def test_conflict_on_another_file_still_stops_and_leaves_branch_intact(
    repo: Path,
) -> None:
    service, base, branche = await _brancher_fichier(
        repo, "README.md", "ticket 9\n", "ticket 8\n"
    )
    avant = await _git(repo, "rev-parse", "HEAD")

    conflits = await service.rejouer_sur(base)

    assert conflits == ("README.md",)
    assert await _git(repo, "rev-parse", "HEAD") == avant
    assert await _git(repo, "rev-parse", "--abbrev-ref", "HEAD") == branche
    assert await service.is_clean()


# --- unit: the id-list union ------------------------------------------------


def test_union_json_lists_merges_documentes_marker() -> None:
    resultat = _union_json_lists(
        json.dumps({"documentes": ["ticket-002", "ticket-001"]}),
        json.dumps({"documentes": ["ticket-003", "ticket-001"]}),
    )

    assert resultat is not None
    assert json.loads(resultat) == {
        "documentes": ["ticket-001", "ticket-002", "ticket-003"]
    }


@pytest.mark.parametrize(
    "illisible",
    [
        '{"dernier_ticket": "ticket-001"}',
        '{"documentes": "ticket-001"}',
        '{"documentes": [], "autre": 1}',
    ],
)
def test_union_json_lists_refuses_unrecognised_shapes(illisible: str) -> None:
    assert _union_json_lists(illisible, '{"documentes": []}') is None
