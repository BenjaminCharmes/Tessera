"""The in-force lessons reach the coder and the reviewer only (ticket-802)."""

import logging
from pathlib import Path

import pytest

from tessera.config import settings
from tessera.services.projets.adr import ROLES_AVEC_LECONS, adr_pertinents
from tessera.services.pipeline.assemblage_run import build_project_context
from tessera.services.gardes.lecons import PLAFOND_OCTETS, section_lecons

LECON = "Quand un double de test manque, le chercher avant de relancer."
PROPOSEE = "Quand une proposition attend, elle ne part nulle part."


def _projet(workspace: Path, lecons: str | None) -> None:
    dossier = workspace / "p"
    (dossier / "memory").mkdir(parents=True)
    (dossier / "CLAUDE.md").write_text("# P\n", encoding="utf-8")
    (dossier / "memory" / "contraintes.md").write_text("# C\n\n- Une règle.\n", encoding="utf-8")
    if lecons is not None:
        (dossier / "memory" / "lecons.md").write_text(lecons, encoding="utf-8")


@pytest.fixture(autouse=True)
def _espace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(settings, "ide_workspace_dir", tmp_path)
    monkeypatch.setattr(settings, "llm_provider", "agent_sdk")
    return tmp_path


FICHIER = f"# L\n\n## Proposées\n- {PROPOSEE}\n\n## En vigueur\n- {LECON}\n"


@pytest.mark.parametrize("role", ["codeur", "reviewer"])
async def test_in_force_lessons_reach_named_roles(_espace: Path, role: str) -> None:
    _projet(_espace, FICHIER)
    contexte = adr_pertinents(await build_project_context("p"), role)
    assert "## Leçons du projet" in contexte
    assert LECON in contexte
    assert "Une règle." in contexte


@pytest.mark.parametrize(
    "role", ["securite", "validateur", "architect", "doc-technique", "role-cree-apres"]
)
async def test_lessons_do_not_reach_other_roles(_espace: Path, role: str) -> None:
    _projet(_espace, FICHIER)
    contexte = adr_pertinents(await build_project_context("p"), role)
    assert LECON not in contexte
    assert "Leçons du projet" not in contexte
    assert "Une règle." in contexte


async def test_proposed_lessons_reach_no_role(_espace: Path) -> None:
    _projet(_espace, FICHIER)
    contexte = await build_project_context("p")
    for role in (*ROLES_AVEC_LECONS, "securite"):
        assert PROPOSEE not in adr_pertinents(contexte, role)


async def test_without_lessons_file_the_context_is_unchanged(_espace: Path) -> None:
    _projet(_espace, None)
    sans_fichier = await build_project_context("p")
    _projet_vide = "# L\n\n## Proposées\n\n## En vigueur\n"
    (_espace / "p" / "memory" / "lecons.md").write_text(_projet_vide, encoding="utf-8")
    assert await build_project_context("p") == sans_fichier
    assert "Leçons" not in sans_fichier
    assert "_Aucune leçon._" not in sans_fichier


def test_section_lecons_truncates_an_oversized_file(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    lignes = "".join(f"- Quand cas {i}, faire {'x' * 150}.\n" for i in range(40))
    (tmp_path / "lecons.md").write_text(f"## En vigueur\n{lignes}", encoding="utf-8")
    with caplog.at_level(logging.WARNING):
        section = section_lecons(tmp_path)
    assert 0 < len(section.encode("utf-8")) <= PLAFOND_OCTETS + 300
    assert section.count("- Quand") < 40
    assert any("lecons" in r.getMessage() or "lecons" in str(r.__dict__) for r in caplog.records)


def test_section_lecons_is_empty_without_in_force_lessons(tmp_path: Path) -> None:
    assert section_lecons(tmp_path) == ""
