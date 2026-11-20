"""Excerpts carried by a refused edition into the corrective brief (ticket-989)."""
from pathlib import Path

import pytest

from tessera.services.documentation.documentation_base import EditionRefusee
from tessera.services.documentation.documentation_editions import appliquer_editions
from tessera.services.documentation.documentation_titres import EXTRAIT_MAX, brief_correction

_FICHIER = "\n".join(
    [
        "# Guide",
        "",
        "Les dépendances de Tessera sont déclarées dans pyproject.toml et le lockfile.",
        "Autre paragraphe sans rapport.",
        "",
        "Lancer le serveur avec make dev.",
        "Fin.",
    ]
)


def _refus(tmp_path: Path, contenu: str, ancien: str) -> EditionRefusee:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "g.md").write_text(contenu, encoding="utf-8")
    edition: dict[str, object] = {"fichier": "docs/g.md", "ancien": ancien, "nouveau": "x"}
    with pytest.raises(EditionRefusee) as info:
        appliquer_editions(tmp_path, [edition])
    return info.value


def _brief(exc: EditionRefusee) -> str:
    return brief_correction("user", "reponse", str(exc), "", None, exc.extrait)


def test_missing_anchor_close_to_a_passage_shows_it(tmp_path: Path) -> None:
    exc = _refus(
        tmp_path, _FICHIER, "Les dépendances du projet sont déclarées dans pyproject.toml"
    )
    brief = _brief(exc)
    assert "3: Les dépendances de Tessera sont déclarées dans pyproject.toml" in brief
    assert "texte introuvable" in str(exc)
    assert "3:" not in str(exc)


def test_anchor_present_twice_shows_both_occurrences_with_context(tmp_path: Path) -> None:
    contenu = "\n".join(["a", "b", "doublon", "c", "d", "e", "f", "g", "doublon", "h"])
    brief = _brief(_refus(tmp_path, contenu, "doublon"))
    assert "Occurrence 1" in brief and "Occurrence 2" in brief
    assert "1: a" in brief and "5: d" in brief
    assert "9: doublon" in brief and "10: h" in brief


def test_anchor_without_similar_passage_has_no_excerpt(tmp_path: Path) -> None:
    exc = _refus(tmp_path, _FICHIER, "zzzzqqqq xxxxwwww 123456789")
    assert exc.extrait == ""
    assert "Passage du fichier visé" not in _brief(exc)


def test_excerpt_is_capped() -> None:
    brief = brief_correction("u", "r", "motif", "", None, "x" * 10_000)
    assert brief.count("x") == EXTRAIT_MAX
