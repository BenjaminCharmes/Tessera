"""Documentation agents can create a file, and a refusal is visible — ticket-342.

Démineur, 2026-10-05 : `doc-fonctionnelle` visait `docs/guide-utilisateur.md`,
qui n'existait pas. `appliquer_editions` refusait le lot entier (« fichier
introuvable »), six fois, pour 2 à 9 minutes de calcul chacune, et
`pipeline-log.md` n'en disait que « 0 fichier(s) ».
"""
from pathlib import Path

import pytest

from tessera.services.documentation import (
    EditionRefusee,
    ResultatDocumentation,
    appliquer_editions,
)
from tests.test_documentation_apres_run import _runner
from tests.test_orchestrator import _FakeGit, _make_orchestrator, _noop


def test_a_missing_docs_file_is_created_from_its_content(tmp_path: Path) -> None:
    ecrits = appliquer_editions(
        tmp_path, [{"fichier": "docs/guide-utilisateur.md", "contenu": "# Guide\n"}]
    )

    assert (tmp_path / "docs" / "guide-utilisateur.md").read_text(encoding="utf-8") == "# Guide\n"
    assert len(ecrits) == 1


def test_a_created_file_can_be_extended_in_the_same_batch(tmp_path: Path) -> None:
    appliquer_editions(tmp_path, [
        {"fichier": "docs/guide.md", "contenu": "# Guide\n\n## Jouer\n"},
        {"fichier": "docs/guide.md", "apres_section": "## Jouer", "texte": "Clique."},
    ])

    assert "Clique." in (tmp_path / "docs" / "guide.md").read_text(encoding="utf-8")


def test_creating_a_file_that_exists_is_refused(tmp_path: Path) -> None:
    # `contenu` écrase tout : il ne sert qu'à créer, jamais à remplacer.
    (tmp_path / "README.md").write_text("# Projet\n", encoding="utf-8")

    with pytest.raises(EditionRefusee, match="existe déjà"):
        appliquer_editions(tmp_path, [{"fichier": "README.md", "contenu": "# Autre\n"}])
    assert (tmp_path / "README.md").read_text(encoding="utf-8") == "# Projet\n"


def test_creating_outside_the_documentation_is_refused(tmp_path: Path) -> None:
    with pytest.raises(EditionRefusee):
        appliquer_editions(tmp_path, [{"fichier": "src/note.md", "contenu": "x"}])
    assert not (tmp_path / "src").exists()


def test_editing_a_missing_file_says_how_to_create_it(tmp_path: Path) -> None:
    with pytest.raises(EditionRefusee, match="contenu"):
        appliquer_editions(
            tmp_path, [{"fichier": "docs/absent.md", "ancien": "a", "nouveau": "b"}]
        )


async def test_the_pipeline_log_names_the_refusal(tmp_path: Path) -> None:
    orc = _make_orchestrator(tmp_path, runner=_runner(), git_workspace=_FakeGit())
    refus = "doc-fonctionnelle : docs/guide-utilisateur.md : fichier introuvable."
    orc._documenter = _documenteur_refuse(refus)

    await orc.run_pipeline("proj", "ticket-001", _noop)

    journal = (tmp_path / "memory" / "pipeline-log.md").read_text(encoding="utf-8")
    assert f"refusé : {refus}" in journal


def _documenteur_refuse(refus: str):  # type: ignore[no-untyped-def]
    from unittest.mock import AsyncMock

    return AsyncMock(return_value=ResultatDocumentation([], [refus], ["ticket-001"]))
