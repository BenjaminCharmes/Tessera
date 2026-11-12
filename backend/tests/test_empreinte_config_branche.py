"""L'empreinte de `.git/config` ignore les sections de branche — ticket-937."""
import subprocess
from pathlib import Path

import pytest

from tessera.services.pipeline.pipeline_empreinte import empreinte, entrees_de_config

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


def _config(depot: Path) -> Path:
    return depot / ".git" / "config"


async def test_a_key_hidden_on_a_branch_header_line_changes_the_fingerprint(depot: Path) -> None:
    avant = await empreinte(_Orch(depot))  # type: ignore[arg-type]
    with _config(depot).open("a", encoding="utf-8") as f:
        f.write('[branch "x"] [core]\n\tfsmonitor = echo-injected\n')
    assert await empreinte(_Orch(depot)) != avant  # type: ignore[arg-type]


async def test_an_include_on_a_branch_header_line_and_its_target_change_the_fingerprint(
    depot: Path,
) -> None:
    cible = _config(depot).parent / "cfg"
    cible.write_text("[user]\n\tname = a\n", encoding="utf-8")
    avant = await empreinte(_Orch(depot))  # type: ignore[arg-type]
    with _config(depot).open("a", encoding="utf-8") as f:
        f.write('[branch "x"] [include]\n\tpath = cfg\n')
    inclus = await empreinte(_Orch(depot))  # type: ignore[arg-type]
    assert inclus != avant
    cible.write_text("[core]\n\tfsmonitor = echo-injected\n", encoding="utf-8")
    assert await empreinte(_Orch(depot)) != inclus  # type: ignore[arg-type]


async def test_branch_remote_and_merge_changes_keep_the_fingerprint(depot: Path) -> None:
    avant = await empreinte(_Orch(depot))  # type: ignore[arg-type]
    _git(depot, "config", "branch.main.remote", "origin")
    _git(depot, "config", "branch.main.merge", "refs/heads/main")
    assert await empreinte(_Orch(depot)) == avant  # type: ignore[arg-type]


def test_entrees_de_config_leaves_branch_keys_out(tmp_path: Path) -> None:
    fichier = tmp_path / "config"
    fichier.write_text(
        '[core]\n\tbare = false\n[branch "a"]\n\tremote = origin\n\tmerge = m\n',
        encoding="utf-8",
    )
    assert entrees_de_config(fichier) == b"core.bare\nfalse"
