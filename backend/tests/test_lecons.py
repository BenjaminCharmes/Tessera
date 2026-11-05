"""Tests of the project lessons module (ticket-801)."""

from datetime import date
from pathlib import Path

import pytest

from tessera.services.lecons import (
    LONGUEUR_MAX,
    PLAFOND_LECONS,
    PLAFOND_OCTETS,
    Lecons,
    ajouter_proposee,
    lire_lecons,
    refus_de_lecon,
)

RETOUR = (
    "Les tests sont rouges : FakeWorkspace ne définit pas la nouvelle méthode "
    "ajoutée à GitWorkspaceService, trois doubles de test sont à mettre à jour."
)
PREUVE = "FakeWorkspace ne définit pas la nouvelle méthode"
LECON_736 = (
    "Quand une méthode s'ajoute à `GitWorkspaceService`, chercher les doubles de test "
    "qui la redéfinissent et les mettre à jour dans le même commit."
)
VIDE = Lecons(en_vigueur=(), proposees=())


def test_lire_lecons_returns_empty_tuples_without_file(tmp_path: Path) -> None:
    assert lire_lecons(tmp_path) == VIDE


def test_lire_lecons_reads_both_sections(tmp_path: Path) -> None:
    (tmp_path / "lecons.md").write_text(
        "# Leçons\n\n## Proposées\n- Quand a, b. (source : ticket-1, 2026-11-05)\n\n"
        "## En vigueur\n- Quand c, d.\n- Quand e, f.\n",
        encoding="utf-8",
    )
    lecons = lire_lecons(tmp_path)
    assert lecons.proposees == ("Quand a, b. (source : ticket-1, 2026-11-05)",)
    assert lecons.en_vigueur == ("Quand c, d.", "Quand e, f.")


def test_refus_accepts_the_ticket_736_lesson() -> None:
    assert refus_de_lecon(LECON_736, PREUVE, VIDE, RETOUR) is None


@pytest.mark.parametrize(
    "texte",
    [
        "Il faut mettre à jour les doubles, toujours.",
        "Quand un double manque sans virgule rien ne va",
        "Quand a, b.\nEt une seconde ligne.",
        "Quand a, ```x``` b.",
        "Quand a, ## b.",
    ],
)
def test_refus_rejects_a_bad_form(texte: str) -> None:
    assert refus_de_lecon(texte, PREUVE, VIDE, RETOUR) is not None


def test_refus_rejects_a_too_long_lesson() -> None:
    texte = "Quand a, " + "x" * LONGUEUR_MAX
    assert "caractères" in (refus_de_lecon(texte, PREUVE, VIDE, RETOUR) or "")


def test_refus_rejects_a_missing_proof() -> None:
    assert refus_de_lecon(LECON_736, "un passage inventé de plus de vingt signes", VIDE, RETOUR)
    assert refus_de_lecon(LECON_736, "court", VIDE, "court")


def test_refus_rejects_an_exact_duplicate_after_normalisation() -> None:
    existante = LECON_736.upper() + " (source : ticket-1, 2026-11-05)"
    existantes = Lecons(en_vigueur=(), proposees=(existante,))
    assert "doublon" in (refus_de_lecon(LECON_736, PREUVE, existantes, RETOUR) or "")


def test_refus_rejects_an_approximate_duplicate() -> None:
    proche = LECON_736.replace("chercher", "trouver").replace("mettre à jour", "corriger")
    existantes = Lecons(en_vigueur=(LECON_736,), proposees=())
    assert "doublon" in (refus_de_lecon(proche, PREUVE, existantes, RETOUR) or "")


def test_refus_rejects_a_named_test_config_file() -> None:
    texte = "Quand un test échoue, ajouter une fixture dans conftest.py."
    assert "configuration" in (refus_de_lecon(texte, PREUVE, VIDE, RETOUR) or "")


def test_refus_rejects_a_weakened_check() -> None:
    texte = "Quand un test échoue, le marquer skip puis continuer."
    assert "vérification" in (refus_de_lecon(texte, PREUVE, VIDE, RETOUR) or "")
    texte = "Quand mypy échoue, ajouter `type: ignore` sur la ligne."
    assert refus_de_lecon(texte, PREUVE, VIDE, RETOUR) is not None


def test_ajouter_proposee_creates_the_file_and_sets_the_source(tmp_path: Path) -> None:
    memory = tmp_path / "memory"
    assert ajouter_proposee(memory, LECON_736, "ticket-736", date(2026, 11, 5)) is True
    lecons = lire_lecons(memory)
    assert lecons.proposees == (f"{LECON_736} (source : ticket-736, 2026-11-05)",)
    assert lecons.en_vigueur == ()


def test_ajouter_proposee_keeps_existing_sections(tmp_path: Path) -> None:
    (tmp_path / "lecons.md").write_text(
        "# Leçons\n\n## Proposées\n\n## En vigueur\n- Quand c, d.\n", encoding="utf-8"
    )
    ajouter_proposee(tmp_path, "Quand a, b.", "ticket-1", date(2026, 11, 5))
    ajouter_proposee(tmp_path, "Quand e, f.", "ticket-2", date(2026, 11, 6))
    lecons = lire_lecons(tmp_path)
    assert len(lecons.proposees) == 2
    assert lecons.en_vigueur == ("Quand c, d.",)


def test_ajouter_proposee_refuses_at_the_byte_ceiling(tmp_path: Path) -> None:
    remplissage = "# Leçons\n\n## Proposées\n\n## En vigueur\n" + "x" * PLAFOND_OCTETS
    (tmp_path / "lecons.md").write_text(remplissage, encoding="utf-8")
    assert ajouter_proposee(tmp_path, "Quand a, b.", "ticket-1", date(2026, 11, 5)) is False
    assert (tmp_path / "lecons.md").read_text(encoding="utf-8") == remplissage


def test_ajouter_proposee_refuses_at_the_lesson_ceiling(tmp_path: Path) -> None:
    lignes = "".join(f"- Q{i}\n" for i in range(PLAFOND_LECONS))
    contenu = f"# Leçons\n\n## Proposées\n\n## En vigueur\n{lignes}"
    (tmp_path / "lecons.md").write_text(contenu, encoding="utf-8")
    assert ajouter_proposee(tmp_path, "Quand a, b.", "ticket-1", date(2026, 11, 5)) is False
    assert (tmp_path / "lecons.md").read_text(encoding="utf-8") == contenu


def test_ajouter_proposee_rejects_a_multiline_text(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        ajouter_proposee(tmp_path, "Quand a,\nb.", "ticket-1", date(2026, 11, 5))
