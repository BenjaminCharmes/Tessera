"""A delivery rebase settles trivial conflicts by rule before the resolver — ticket-548."""
import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path

import pytest

from tessera.services.git_workspace import GitWorkspaceService

_ANCETRE = {"a.py": "import os\n", "b.py": "version = 0\n"}


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


async def _ecrire(repo: Path, fichiers: dict[str, str], message: str) -> None:
    for nom, contenu in fichiers.items():
        (repo / nom).write_bytes(contenu.encode("utf-8"))
    await _git(repo, "commit", "-q", "-am", message)


@pytest.fixture
async def repo(tmp_path: Path) -> Path:
    root = tmp_path / "projet"
    root.mkdir()
    await _git(root, "init", "-q", "-b", "main")
    await _git(root, "config", "user.email", "test@tessera.local")
    await _git(root, "config", "user.name", "Tessera test")
    await _git(root, "config", "core.autocrlf", "false")
    await _git(root, "config", "merge.conflictStyle", "merge")
    # Aucune normalisation des fins de ligne : le test CRLF doit les retrouver telles quelles.
    (root / ".gitattributes").write_text("* -text\n", encoding="utf-8")
    for nom, contenu in _ANCETRE.items():
        (root / nom).write_bytes(contenu.encode("utf-8"))
    await _git(root, "add", ".")
    await _git(root, "commit", "-q", "-m", "init")
    return root


async def _diverger(repo: Path, ticket: dict[str, str], base: dict[str, str]) -> str:
    """A ticket branch and an advanced `main`, both rewriting the same files."""
    await _git(repo, "checkout", "-q", "-b", "ticket-548-regles")
    await _ecrire(repo, ticket, "feat: ticket-548")
    await _git(repo, "checkout", "-q", "main")
    await _ecrire(repo, base, "chore: base")
    await _git(repo, "checkout", "-q", "ticket-548-regles")
    return "main"


def _enregistrer(
    appels: list[tuple[str, ...]],
) -> Callable[[tuple[str, ...]], Awaitable[None]]:
    async def resolveur(fichiers: tuple[str, ...]) -> None:
        appels.append(fichiers)

    return resolveur


async def test_a_file_settled_by_rule_never_reaches_the_resolver(repo: Path) -> None:
    base = await _diverger(
        repo, {"a.py": "import os\nimport sys\n"}, {"a.py": "import os\nimport re\n"}
    )
    appels: list[tuple[str, ...]] = []
    service = GitWorkspaceService(repo)

    conflits = await service.rejouer_sur(base, resolveur=_enregistrer(appels))

    assert conflits == ()
    assert appels == [], "the resolver agent is not called when a rule settles it"
    # Le côté upstream d'abord, puis l'import du ticket.
    assert (repo / "a.py").read_text(encoding="utf-8") == "import os\nimport re\nimport sys\n"
    assert service.regles_appliquees == (("a.py", "imports"),)
    assert await _git(repo, "status", "--porcelain") == ""
    assert not (repo / ".git" / "rebase-merge").exists()
    assert await _git(repo, "log", "-1", "--format=%s") == "feat: ticket-548"


async def test_a_rule_settles_the_file_without_any_resolver(repo: Path) -> None:
    base = await _diverger(
        repo, {"a.py": "import os\nimport sys\n"}, {"a.py": "import os\nimport re\n"}
    )

    conflits = await GitWorkspaceService(repo).rejouer_sur(base)

    assert conflits == ()


async def test_a_file_with_a_block_without_rule_reaches_the_resolver_intact(
    repo: Path,
) -> None:
    base = await _diverger(repo, {"b.py": "version = 2\n"}, {"b.py": "version = 3\n"})
    appels: list[tuple[str, ...]] = []
    vus: list[str] = []

    async def resolveur(fichiers: tuple[str, ...]) -> None:
        appels.append(fichiers)
        vus.append((repo / "b.py").read_text(encoding="utf-8"))

    service = GitWorkspaceService(repo)
    avant = await _git(repo, "rev-parse", "HEAD")

    conflits = await service.rejouer_sur(base, resolveur=resolveur)

    assert appels == [("b.py",)]
    assert "<<<<<<<" in vus[0] and "|||||||" not in vus[0], "the resolver sees git's own style"
    assert conflits == ("b.py",)
    assert service.regles_appliquees == ()
    assert await _git(repo, "rev-parse", "HEAD") == avant
    assert await service.is_clean()


async def test_a_mixed_rebase_sends_only_the_unsettled_file_to_the_resolver(
    repo: Path,
) -> None:
    base = await _diverger(
        repo,
        {"a.py": "import os\nimport sys\n", "b.py": "version = 2\n"},
        {"a.py": "import os\nimport re\n", "b.py": "version = 3\n"},
    )
    appels: list[tuple[str, ...]] = []

    async def resolveur(fichiers: tuple[str, ...]) -> None:
        appels.append(fichiers)
        (repo / "b.py").write_text("version = 5\n", encoding="utf-8")

    service = GitWorkspaceService(repo)

    conflits = await service.rejouer_sur(base, resolveur=resolveur)

    assert conflits == ()
    assert appels == [("b.py",)]
    assert (repo / "a.py").read_text(encoding="utf-8") == "import os\nimport re\nimport sys\n"
    assert (repo / "b.py").read_text(encoding="utf-8") == "version = 5\n"
    assert service.regles_appliquees == (("a.py", "imports"),)
    assert await _git(repo, "status", "--porcelain") == ""


async def test_a_failed_resolver_aborts_the_rule_settled_file_too(repo: Path) -> None:
    base = await _diverger(
        repo,
        {"a.py": "import os\nimport sys\n", "b.py": "version = 2\n"},
        {"a.py": "import os\nimport re\n", "b.py": "version = 3\n"},
    )
    service = GitWorkspaceService(repo)
    avant = await _git(repo, "rev-parse", "HEAD")

    conflits = await service.rejouer_sur(base, resolveur=_enregistrer([]))

    assert conflits == ("b.py",)
    assert service.regles_appliquees == ()
    assert await _git(repo, "rev-parse", "HEAD") == avant
    assert (repo / "a.py").read_text(encoding="utf-8") == "import os\nimport sys\n"


async def test_crlf_line_endings_are_kept_in_a_settled_file(repo: Path) -> None:
    await _git(repo, "checkout", "-q", "-b", "prep")
    await _ecrire(repo, {"a.py": "import os\r\n"}, "chore: crlf")
    await _git(repo, "checkout", "-q", "main")
    await _git(repo, "merge", "-q", "--ff-only", "prep")
    base = await _diverger(
        repo, {"a.py": "import os\r\nimport sys\r\n"}, {"a.py": "import os\r\nimport re\r\n"}
    )

    conflits = await GitWorkspaceService(repo).rejouer_sur(base)

    assert conflits == ()
    contenu = (repo / "a.py").read_bytes()
    assert contenu == b"import os\r\nimport re\r\nimport sys\r\n"


async def test_a_second_rebase_forgets_the_previous_rules(repo: Path) -> None:
    base = await _diverger(
        repo, {"a.py": "import os\nimport sys\n"}, {"a.py": "import os\nimport re\n"}
    )
    service = GitWorkspaceService(repo)
    await service.rejouer_sur(base)
    assert service.regles_appliquees

    await service.rejouer_sur(base)

    assert service.regles_appliquees == ()
