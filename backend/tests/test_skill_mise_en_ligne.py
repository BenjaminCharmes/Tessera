"""The `mise-en-ligne` plugin skill exists and carries its rules — ticket-447."""
from pathlib import Path

import pytest

_SKILL = (
    Path(__file__).resolve().parents[2]
    / "agents" / "plugin" / "skills" / "mise-en-ligne" / "SKILL.md"
)


@pytest.fixture(scope="module")
def content() -> str:
    return _SKILL.read_text(encoding="utf-8")


def _frontmatter(content: str) -> dict[str, str]:
    lignes = content.splitlines()
    assert lignes[0] == "---", "frontmatter must open the file"
    fin = lignes.index("---", 1)
    champs: dict[str, str] = {}
    for ligne in lignes[1:fin]:
        cle, _, valeur = ligne.partition(":")
        champs[cle.strip()] = valeur.strip()
    return champs


def test_skill_file_exists() -> None:
    assert _SKILL.is_file()


def test_frontmatter_declares_name_and_use_when_description(content: str) -> None:
    champs = _frontmatter(content)

    assert champs["name"] == "mise-en-ligne"
    assert champs["description"].startswith("Use when")


def test_skill_stays_under_200_lines(content: str) -> None:
    assert len(content.splitlines()) < 200


def test_table_lists_twenty_points_legal_notices_included(content: str) -> None:
    lignes = [ligne for ligne in content.splitlines() if ligne.startswith("| ")]
    numerotees = [ligne for ligne in lignes if ligne.split("|")[1].strip().isdigit()]

    assert len(numerotees) == 20
    assert any("Mentions légales" in ligne for ligne in numerotees)


def test_consent_exempt_analytics_waives_the_cookie_banner(content: str) -> None:
    assert "exemptée de consentement" in content
    assert "dispense" in content
    assert "vanilla-cookieconsent" in content


def test_react_helmet_async_is_forbidden_in_favour_of_native_metadata(
    content: str,
) -> None:
    assert "N'ajoute pas `react-helmet-async`" in content
    assert "React 19" in content


def test_legal_templates_use_the_placeholder_marker(content: str) -> None:
    assert "À_REMPLACER" in content
    assert "bloquant" in content
