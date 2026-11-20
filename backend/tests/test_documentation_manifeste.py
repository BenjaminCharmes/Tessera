"""The agents.json description written by the documentation is committed — ticket-866.

Le service de documentation réécrit la clé `description` d'`agents.json` ; or
`commit_all` exclut ce fichier de politique du run (ticket-296) et le laissait
modifié dans l'arbre : la livraison refusait l'arbre sale. Ici, un vrai dépôt
temporaire : ce qui compte est l'état de git, pas un appel simulé.
"""
import subprocess
from collections.abc import Awaitable, Callable
from pathlib import Path

import pytest

from tessera.models.ticket import TicketStatus
from tessera.services.documentation.documentation import ResultatDocumentation
from tessera.services.documentation.documentation_description import remplacer_description
from tessera.services.git_workspace import GitWorkspaceService
from tessera.services.noyau.pipeline_events import EventType, OrchestratorEvent, PipelineResult
from tessera.services.pipeline.orchestrator import Orchestrator
from tessera.services.pipeline.pipeline_documentation import documenter_le_run
from tests.test_orchestrator import _make_orchestrator

_ORIGINE = '{\n  "autonomy": "commit",\n  "description": "ancienne"\n}\n'
_NOUVELLE = "Nouvelle description du produit."


def _git(cwd: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    )
    return proc.stdout.strip()


@pytest.fixture
def depot(tmp_path: Path) -> Path:
    racine = tmp_path / "projet"
    racine.mkdir()
    _git(racine, "init", "-q")
    _git(racine, "config", "user.email", "test@tessera.local")
    _git(racine, "config", "user.name", "Tessera test")
    (racine / "agents.json").write_text(_ORIGINE, encoding="utf-8")
    _git(racine, "add", "agents.json")
    _git(racine, "commit", "-q", "-m", "init")
    return racine


def _ecrire_description(projet: Path) -> Callable[[], Awaitable[ResultatDocumentation]]:
    """A documenter that rewrites the description like the real service does."""

    async def documenter() -> ResultatDocumentation:
        manifeste = projet / "agents.json"
        src = manifeste.read_bytes().decode("utf-8")
        manifeste.write_bytes(remplacer_description(src, _NOUVELLE).encode("utf-8"))
        return ResultatDocumentation(
            [str(manifeste)], [], ["ticket-001"], marqueur_ecrit=True
        )

    return documenter


async def _documenter(
    tmp_path: Path, depot: Path
) -> tuple[Orchestrator, list[OrchestratorEvent], list[str]]:
    git = GitWorkspaceService(depot)
    await git.create_branch("ticket-866", "essai")
    orc = _make_orchestrator(tmp_path, git_workspace=git, project_path=depot)
    orc._documenter = _ecrire_description(depot)
    journal: list[str] = []
    orc._log = journal.append  # type: ignore[method-assign]
    evenements: list[OrchestratorEvent] = []

    async def capter(ev: OrchestratorEvent) -> None:
        evenements.append(ev)

    resultat = PipelineResult(
        ticket_id="ticket-866", final_status=TicketStatus.in_review, rounds=1,
        approved=True, branch="ticket-866-essai",
    )
    await documenter_le_run(orc, resultat, capter)
    return orc, evenements, journal


async def test_an_accepted_description_leaves_a_clean_tree_and_is_committed(
    tmp_path: Path, depot: Path
) -> None:
    await _documenter(tmp_path, depot)
    assert _git(depot, "status", "--porcelain") == ""
    assert _NOUVELLE in _git(depot, "show", "HEAD:agents.json")
    assert _git(depot, "log", "-1", "--format=%s").startswith("docs: update documentation")


async def test_a_manifest_change_made_before_the_lot_refuses_the_description(
    tmp_path: Path, depot: Path
) -> None:
    modifie = _ORIGINE.replace('"commit"', '"pr"')
    (depot / "agents.json").write_text(modifie, encoding="utf-8")
    tete = _git(depot, "rev-parse", "HEAD")

    _, evenements, journal = await _documenter(tmp_path, depot)

    # La modification de l'interface reste, intacte, hors de tout commit.
    assert (depot / "agents.json").read_text(encoding="utf-8") == modifie
    assert _git(depot, "rev-parse", "HEAD") == tete
    assert _git(depot, "status", "--porcelain", "--untracked-files=no") == "M agents.json"
    doc = [e for e in evenements if e.type is EventType.DOC_UPDATED]
    assert len(doc) == 1
    assert doc[0].data["fichiers"] == []
    assert any("agents.json modifié pendant le run" in r for r in doc[0].data["refus"])
    assert any("agents.json modifié pendant le run" in ligne for ligne in journal)


async def test_est_modifie_reports_a_tracked_change_only(depot: Path) -> None:
    git = GitWorkspaceService(depot)
    assert await git.est_modifie("agents.json") is False
    (depot / "agents.json").write_text("{}\n", encoding="utf-8")
    assert await git.est_modifie("agents.json") is True
    (depot / "neuf.txt").write_text("x\n", encoding="utf-8")
    assert await git.est_modifie("neuf.txt") is False


async def test_stager_chemins_stages_the_named_file_without_committing(depot: Path) -> None:
    git = GitWorkspaceService(depot)
    (depot / "agents.json").write_text("{}\n", encoding="utf-8")
    (depot / "autre.txt").write_text("x\n", encoding="utf-8")
    tete = _git(depot, "rev-parse", "HEAD")
    await git.stager_chemins(["agents.json"])
    assert _git(depot, "diff", "--cached", "--name-only") == "agents.json"
    assert _git(depot, "rev-parse", "HEAD") == tete
