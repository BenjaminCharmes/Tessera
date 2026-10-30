"""Le lot de documentation tient aussi le CLAUDE.md du projet — ticket-244.

Un CLAUDE.md qui décrit ce qui n'existe plus est une consigne fausse, chargée
dans chaque session. Mais un CLAUDE.md qu'un agent allonge à chaque lot finit
ignoré : chaque ligne concurrence les autres. Le projet le déclare, seul
`doc-technique` y touche, et le fichier ne franchit pas son budget.
"""
import json
from pathlib import Path

import pytest

from tessera.services.documentation import (
    DocumentationService,
    EditionRefusee,
    appliquer_editions,
)
from tessera.services.documentation_claude_md import BUDGET_CLAUDE_MD
from tessera.services.providers.base import ProviderResult
from tests.matiere_factice import matiere_factice


def _depot(tmp_path: Path, claude_md: str = "# Projet\n\nLe testeur est désactivé.\n") -> Path:
    (tmp_path / "CLAUDE.md").write_text("# Racine — ne pas toucher\n", encoding="utf-8")
    projet = tmp_path / "projects" / "p"
    projet.mkdir(parents=True)
    (projet / "CLAUDE.md").write_text(claude_md, encoding="utf-8")
    return projet


def test_claude_md_designe_celui_du_projet_pas_celui_de_la_racine(tmp_path: Path) -> None:
    projet = _depot(tmp_path)

    appliquer_editions(
        tmp_path,
        [{"fichier": "CLAUDE.md", "ancien": "est désactivé", "nouveau": "est actif"}],
        claude_md=projet / "CLAUDE.md",
    )

    assert "est actif" in (projet / "CLAUDE.md").read_text(encoding="utf-8")
    assert (tmp_path / "CLAUDE.md").read_text(encoding="utf-8") == "# Racine — ne pas toucher\n"


def test_sans_declaration_claude_md_est_refuse(tmp_path: Path) -> None:
    projet = _depot(tmp_path)

    with pytest.raises(EditionRefusee):
        appliquer_editions(
            tmp_path,
            [{"fichier": "CLAUDE.md", "ancien": "est désactivé", "nouveau": "est actif"}],
        )

    assert "désactivé" in (projet / "CLAUDE.md").read_text(encoding="utf-8")


def test_une_edition_qui_franchit_le_budget_est_refusee(tmp_path: Path) -> None:
    projet = _depot(tmp_path)
    ajout = "x" * BUDGET_CLAUDE_MD

    with pytest.raises(EditionRefusee, match="budget"):
        appliquer_editions(
            tmp_path,
            [{"fichier": "CLAUDE.md", "ancien": "est désactivé", "nouveau": ajout}],
            claude_md=projet / "CLAUDE.md",
        )

    assert "désactivé" in (projet / "CLAUDE.md").read_text(encoding="utf-8")


def test_un_fichier_deja_trop_long_peut_raccourcir_pas_grandir(tmp_path: Path) -> None:
    long = "# P\n\n" + "a" * BUDGET_CLAUDE_MD + "\nligne à retirer\n"
    projet = _depot(tmp_path, claude_md=long)
    cible = projet / "CLAUDE.md"

    appliquer_editions(
        tmp_path,
        [{"fichier": "CLAUDE.md", "ancien": "ligne à retirer\n", "nouveau": ""}],
        claude_md=cible,
    )
    assert "ligne à retirer" not in cible.read_text(encoding="utf-8")

    with pytest.raises(EditionRefusee, match="budget"):
        appliquer_editions(
            tmp_path,
            [{"fichier": "CLAUDE.md", "ancien": "# P\n", "nouveau": "# P\n\nUne règle de plus.\n"}],
            claude_md=cible,
        )


def test_agents_md_is_given_and_editable_when_claude_md_is(tmp_path: Path) -> None:
    projet = _depot(tmp_path)
    agents = tmp_path / "AGENTS.md"
    agents.write_text("# Agents\n\nLe testeur est désactivé.\n", encoding="utf-8")
    edition = [{"fichier": "AGENTS.md", "ancien": "est désactivé", "nouveau": "est actif"}]

    # Sans déclaration, `agents_md` n'est pas fourni : l'édition est refusée.
    with pytest.raises(EditionRefusee):
        appliquer_editions(tmp_path, edition)
    assert "désactivé" in agents.read_text(encoding="utf-8")

    appliquer_editions(tmp_path, edition, claude_md=projet / "CLAUDE.md", agents_md=agents)
    assert "est actif" in agents.read_text(encoding="utf-8")

    # Même budget que le CLAUDE.md.
    with pytest.raises(EditionRefusee, match="AGENTS.md dépasserait"):
        appliquer_editions(
            tmp_path,
            [{"fichier": "AGENTS.md", "ancien": "est actif", "nouveau": "x" * BUDGET_CLAUDE_MD}],
            agents_md=agents,
        )


async def test_agents_md_reaches_only_doc_technique_and_only_with_the_declaration(
    tmp_path: Path,
) -> None:
    projet = _depot(tmp_path)
    (tmp_path / "AGENTS.md").write_text("# Agents\n\nMARQUE-DES-AGENTS\n", encoding="utf-8")
    (projet / "memory").mkdir()
    (projet / "memory" / "documentation.json").write_text('{"documentes": []}', encoding="utf-8")
    (projet / "tickets" / "done").mkdir(parents=True)
    (projet / "tickets" / "done" / "ticket-001-x.md").write_text(
        "---\ntitle: \"x\"\n---\n# x\n", encoding="utf-8"
    )
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    for role in ("doc-technique", "doc-fonctionnelle"):
        (prompts / f"{role}.md").write_text("sys", encoding="utf-8")

    for declare in (True, False):
        recus: dict[str, str] = {}
        service = DocumentationService(
            _Provider("?", recus),  # type: ignore[arg-type]
            prompts,
            fournisseur=lambda role: (_Provider(role, recus), None),  # type: ignore[arg-type,return-value]
            claude_md=projet / "CLAUDE.md" if declare else None,
            matiere=matiere_factice(),
        )
        await service.mettre_a_jour(projet, racine_doc=tmp_path)
        assert ("MARQUE-DES-AGENTS" in recus["doc-technique"]) is declare
        assert "MARQUE-DES-AGENTS" not in recus["doc-fonctionnelle"]
        (projet / "memory" / "documentation.json").write_text(
            '{"documentes": []}', encoding="utf-8"
        )


class _Provider:
    def __init__(self, role: str, recus: dict[str, str]) -> None:
        self._role = role
        self._recus = recus

    async def complete(self, *, system: str, user: str, model: str, max_tokens: int) -> ProviderResult:
        self._recus[self._role] = user
        return ProviderResult(content='{"editions": []}', input_tokens=0, output_tokens=0)


async def test_seul_doc_technique_recoit_le_claude_md(tmp_path: Path) -> None:
    projet = _depot(tmp_path, claude_md="# Projet\n\nMARQUE-DU-CLAUDE-MD\n")
    (projet / "memory").mkdir()
    (projet / "memory" / "documentation.json").write_text(
        json.dumps({"documentes": []}), encoding="utf-8"
    )
    (projet / "tickets" / "done").mkdir(parents=True)
    (projet / "tickets" / "done" / "ticket-001-x.md").write_text(
        "---\ntitle: \"x\"\n---\n# x\n", encoding="utf-8"
    )
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    for role in ("doc-technique", "doc-fonctionnelle"):
        (prompts / f"{role}.md").write_text("sys", encoding="utf-8")
    recus: dict[str, str] = {}

    service = DocumentationService(
        _Provider("?", recus),  # type: ignore[arg-type]
        prompts,
        fournisseur=lambda role: (_Provider(role, recus), None),  # type: ignore[arg-type,return-value]
        claude_md=projet / "CLAUDE.md",
        matiere=matiere_factice(),
    )
    await service.mettre_a_jour(projet, racine_doc=tmp_path)

    assert "MARQUE-DU-CLAUDE-MD" in recus["doc-technique"]
    assert "MARQUE-DU-CLAUDE-MD" not in recus["doc-fonctionnelle"]
