"""L'empreinte de `.git/config` ignore les sections de branche — ticket-937."""
import subprocess
from pathlib import Path

import pytest

from tessera.services.pipeline.pipeline_empreinte import empreinte, sans_sections_de_branche

_IDENTITE = ["-c", "user.name=Test", "-c", "user.email=test@example.com"]


class _Orch:
    def __init__(self, projet: Path) -> None:
        self._project_path = projet
        self._test_command = None


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *_IDENTITE, *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def depot(tmp_path: Path) -> Path:
    racine = tmp_path / "depot"
    racine.mkdir()
    _git(racine, "init", "-b", "main")
    (racine / "agents.json").write_text("{}", encoding="utf-8")
    _git(racine, "add", "agents.json")
    _git(racine, "commit", "-m", "init")
    return racine


async def test_a_branch_upstream_written_by_push_u_does_not_change_the_fingerprint(depot: Path) -> None:
    avant = await empreinte(_Orch(depot))  # type: ignore[arg-type]
    _git(depot, "config", "branch.ticket-1.remote", "origin")
    _git(depot, "config", "branch.ticket-1.merge", "refs/heads/ticket-1")
    _git(depot, "config", "branch.main.vscode-merge-base", "origin/main")
    assert await empreinte(_Orch(depot)) == avant  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("cle", "valeur"),
    [
        ("core.fsmonitor", "evil.sh"),
        ("core.hooksPath", "/tmp/hooks"),
        ("diff.external", "evil.sh"),
        ("filter.x.clean", "evil.sh"),
        ("remote.origin.url", "https://example.com/elsewhere.git"),
    ],
)
async def test_a_key_outside_branch_sections_still_changes_the_fingerprint(
    depot: Path, cle: str, valeur: str
) -> None:
    avant = await empreinte(_Orch(depot))  # type: ignore[arg-type]
    _git(depot, "config", cle, valeur)
    assert await empreinte(_Orch(depot)) != avant  # type: ignore[arg-type]


def test_branch_sections_are_dropped_and_the_rest_is_kept() -> None:
    contenu = (
        b'[core]\n\tbare = false\n'
        b'[branch "a"]\n\tremote = origin\n\tmerge = refs/heads/a\n'
        b'[remote "origin"]\n\turl = https://example.com/r.git\n'
        b'  [branch "b"]\n\tremote = origin\n'
        b'[filter "x"]\n\tclean = cat\n'
    )
    assert sans_sections_de_branche(contenu) == (
        b'[core]\n\tbare = false\n'
        b'[remote "origin"]\n\turl = https://example.com/r.git\n'
        b'[filter "x"]\n\tclean = cat\n'
    )
