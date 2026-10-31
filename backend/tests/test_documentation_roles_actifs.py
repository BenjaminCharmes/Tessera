"""A documentation role the project does not keep active is not called — ticket-534.

Signalement du 22/10 : `doc-technique` était à `"active": false` et le run
suivant a quand même écrit la doc. Les fournisseurs LLM sont des doubles, un
par rôle, pour savoir lequel a été appelé.
"""
import json
from pathlib import Path

import pytest

from tessera.config import settings
from tessera.services import documenteur_run
from tessera.services.documenteur_run import documenteur
from tessera.services import documentation
from tests.matiere_factice import matiere_factice
from tests.test_providers_base import FakeProvider

PROJET = "demo"
ROLES = ("doc-technique", "doc-fonctionnelle")
EDITION = json.dumps(
    {"editions": [{
        "fichier": "README.md", "ancien": "Avant.", "nouveau": "Après.",
        "preuve": [{"fichier": "src/ticket-2.py", "extrait": "code de ticket-2"}],
    }]}
)
MARQUEUR = json.dumps({"documentes": ["ticket-1"]})


def _agent(role: str, active: bool) -> dict[str, object]:
    return {
        "role": role, "model": "m", "max_tokens": 1,
        "prompt_file": f"{role}.md", "active": active,
    }


def _fiche(identifiant: str) -> str:
    return (
        f'---\nid: {identifiant}\ntitle: "{identifiant}"\ntype: feat\n'
        f"status: done\n---\n\n# {identifiant}\n"
    )


def _ecrire(chemin: Path, contenu: str) -> None:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(contenu, encoding="utf-8")


@pytest.fixture
def fournisseurs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, FakeProvider]:
    """A project with one ticket waiting for its documentation, and one double per role."""
    projet = tmp_path / PROJET
    _ecrire(projet / "CLAUDE.md", "# Demo\n")
    _ecrire(projet / "README.md", "Avant.\n")
    _ecrire(projet / "tickets" / "done" / "ticket-1-a.md", _fiche("ticket-1"))
    _ecrire(projet / "tickets" / "done" / "ticket-2-b.md", _fiche("ticket-2"))
    _ecrire(projet / "memory" / "documentation.json", MARQUEUR)
    prompts = tmp_path / "prompts"
    for role in ROLES:
        _ecrire(prompts / f"{role}.md", f"Tu es {role}.")
    doubles = {role: FakeProvider('{"editions": []}') for role in ROLES}
    doubles["doc-technique"].set_content(EDITION)
    monkeypatch.setattr(settings, "ide_prompts_dir", prompts)
    monkeypatch.setattr(settings, "ide_workspace_dir", tmp_path)
    monkeypatch.setattr(
        documenteur_run, "provider_pour_role", lambda _chemin, role, **_: doubles[role]
    )
    # Le diff d'un ticket se prend sur sa branche : ces tickets n'en ont pas.
    monkeypatch.setattr(documentation, "matiere_du_lot", matiere_factice())
    return doubles


def _declarer(tmp_path: Path, agents: list[dict[str, object]]) -> None:
    _ecrire(tmp_path / PROJET / "agents.json", json.dumps({"agents": agents}))


def _appeles(doubles: dict[str, FakeProvider]) -> list[str]:
    return [role for role, double in doubles.items() if double.calls]


async def test_inactive_documentation_role_is_not_called(
    tmp_path: Path, fournisseurs: dict[str, FakeProvider]
) -> None:
    _declarer(tmp_path, [_agent("doc-technique", False), _agent("doc-fonctionnelle", True)])

    await documenteur(PROJET)()

    assert _appeles(fournisseurs) == ["doc-fonctionnelle"]


async def test_undeclared_documentation_role_is_not_called(
    tmp_path: Path, fournisseurs: dict[str, FakeProvider]
) -> None:
    _declarer(tmp_path, [_agent("doc-technique", True)])

    await documenteur(PROJET)()

    assert _appeles(fournisseurs) == ["doc-technique"]


async def test_no_active_documentation_role_writes_nothing_and_keeps_the_marker(
    tmp_path: Path, fournisseurs: dict[str, FakeProvider]
) -> None:
    _declarer(tmp_path, [_agent("doc-technique", False)])

    resultat = await documenteur(PROJET)()

    projet = tmp_path / PROJET
    assert _appeles(fournisseurs) == []
    assert resultat.fichiers_modifies == []
    assert resultat.tickets == []
    assert resultat.marqueur_ecrit is False
    assert (projet / "README.md").read_text(encoding="utf-8") == "Avant.\n"
    assert (projet / "memory" / "documentation.json").read_text(encoding="utf-8") == MARQUEUR


async def test_project_without_manifest_calls_no_documentation_role(
    tmp_path: Path, fournisseurs: dict[str, FakeProvider]
) -> None:
    resultat = await documenteur(PROJET)()

    assert _appeles(fournisseurs) == []
    assert resultat.marqueur_ecrit is False


async def test_two_active_documentation_roles_are_both_called(
    tmp_path: Path, fournisseurs: dict[str, FakeProvider]
) -> None:
    _declarer(tmp_path, [_agent(role, True) for role in ROLES])

    resultat = await documenteur(PROJET)()

    assert _appeles(fournisseurs) == list(ROLES)
    assert resultat.marqueur_ecrit is True
    marqueur = json.loads(
        (tmp_path / PROJET / "memory" / "documentation.json").read_text("utf-8")
    )
    assert marqueur["documentes"] == ["ticket-1", "ticket-2"]
