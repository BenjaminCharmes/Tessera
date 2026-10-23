"""The documentation of a worktree run writes in the worktree, never in the checkout — ADR-056.

Signalement du 22/10 : l'étape documentation (`_documenteur`) calculait ses
chemins sur le dossier réel du projet, alors que tout le reste du run recevait
le worktree. Les fichiers de doc et le marqueur atterrissaient dans le checkout,
hors de toute branche. Vrai dépôt avec origin local ; les fournisseurs LLM sont
des doubles.
"""
import json
from pathlib import Path

import pytest

from tessera.config import settings
from tessera.routers import orchestrator as routeur
from tessera.services import documentation
from tessera.services.politique_run import PolitiqueRun
from tessera.services.run_dans_worktree import ouvrir_worktree
from tessera.services.run_worktree import RunWorktree
from tests.depot_worktree import construire, git
from tests.matiere_factice import matiere_factice
from tests.test_providers_base import FakeProvider

PROJET = "checkout"
TICKET = "ticket-3"
DECLARATION = {
    "autonomy": "pr",
    "artifacts": "tracked",
    "base_branch": "develop",
    "worktree": {"populate": [{"path": "cache", "mode": "copy"}]},
    # Un rôle de documentation se déclare pour être appelé (ticket-534).
    "agents": [
        {"role": role, "model": "m", "max_tokens": 1, "prompt_file": f"{role}.md"}
        for role in ("doc-technique", "doc-fonctionnelle")
    ],
}
EDITION = {
    "editions": [
        {
            "fichier": "README.md", "ancien": "Texte ancien.", "nouveau": "Texte nouveau.",
            "preuve": [{"fichier": "src/ticket-2.py", "extrait": "code de ticket-2"}],
        }
    ]
}
README_AVANT = "# Projet\n\nTexte ancien.\n"


def _fiche(identifiant: str) -> str:
    return "\n".join([
        "---", f"id: {identifiant}", f'title: "{identifiant}"', "type: feat",
        "status: done", "---", "", f"# {identifiant}", "",
    ])


def _ecrire(repo: Path, chemin: str, contenu: str) -> None:
    fichier = repo / chemin
    fichier.parent.mkdir(parents=True, exist_ok=True)
    fichier.write_text(contenu, encoding="utf-8")


@pytest.fixture
def depot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A project with one documented ticket and one waiting for its documentation."""
    repo = construire(tmp_path, monkeypatch)
    _ecrire(repo, "agents.json", json.dumps(DECLARATION))
    _ecrire(repo, "CLAUDE.md", "# Projet\n")
    _ecrire(repo, "README.md", README_AVANT)
    _ecrire(repo, "tickets/done/ticket-1-a.md", _fiche("ticket-1"))
    _ecrire(repo, "tickets/done/ticket-2-b.md", _fiche("ticket-2"))
    _ecrire(repo, "memory/documentation.json", json.dumps({"documentes": ["ticket-1"]}))
    git(repo, "add", ".")
    git(repo, "commit", "-m", "add project")
    git(repo, "push", "origin", "develop")
    prompts = tmp_path / "prompts"
    for role in ("doc-technique", "doc-fonctionnelle"):
        _ecrire(prompts, f"{role}.md", f"Tu es {role}.")
    monkeypatch.setattr(settings, "ide_prompts_dir", prompts)
    monkeypatch.setattr(settings, "ide_workspace_dir", repo.parent)
    monkeypatch.setattr(settings, "llm_provider", "agent_sdk")
    monkeypatch.setattr(routeur, "provider_pour_role", _fournisseurs_factices)
    # Le diff d'un ticket se prend sur sa branche : ces tickets n'en ont pas.
    monkeypatch.setattr(documentation, "matiere_du_lot", matiere_factice())
    return repo


def _fournisseurs_factices(
    project_path: Path, role: str, **_: object
) -> FakeProvider:
    # `doc-technique` corrige le README ; `doc-fonctionnelle` n'a rien à dire.
    return FakeProvider(json.dumps(EDITION if role == "doc-technique" else {"editions": []}))


async def _worktree(depot: Path) -> RunWorktree:
    ouvert = await ouvrir_worktree(
        depot, PROJET, TICKET, "demo", PolitiqueRun.lire(depot)
    )
    assert ouvert is not None
    return ouvert[0]


async def test_documentation_of_a_worktree_run_writes_under_the_worktree(depot: Path) -> None:
    wt = await _worktree(depot)
    avant = git(depot, "status", "--porcelain")

    documenter = routeur._documenteur(PROJET, PolitiqueRun.lire(depot), wt)
    resultat = await documenter()

    readme = wt.projet / "README.md"
    assert readme.read_text(encoding="utf-8") == "# Projet\n\nTexte nouveau.\n"
    marqueur = json.loads((wt.projet / "memory" / "documentation.json").read_text("utf-8"))
    assert marqueur["documentes"] == ["ticket-1", "ticket-2"]
    assert [Path(f).resolve() for f in resultat.fichiers_modifies] == [readme.resolve()]
    # Le checkout est identique, fichier par fichier et pour git.
    assert (depot / "README.md").read_text(encoding="utf-8") == README_AVANT
    assert json.loads((depot / "memory" / "documentation.json").read_text("utf-8")) == {
        "documentes": ["ticket-1"]
    }
    assert git(depot, "status", "--porcelain") == avant


async def test_documentation_without_a_worktree_writes_under_the_real_project(
    depot: Path,
) -> None:
    politique = PolitiqueRun.lire(depot)

    resultat = await routeur._documenteur(PROJET, politique)()

    racine = politique.racine_ecriture(depot)
    assert [Path(f).resolve() for f in resultat.fichiers_modifies] == [
        (racine / "README.md").resolve()
    ]
    assert (racine / "README.md").read_text(encoding="utf-8") == "# Projet\n\nTexte nouveau.\n"
    marqueur = json.loads((depot / "memory" / "documentation.json").read_text("utf-8"))
    assert marqueur["documentes"] == ["ticket-1", "ticket-2"]
