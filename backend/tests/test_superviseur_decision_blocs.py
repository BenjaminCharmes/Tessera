"""The blocks a supervisor decision moves or drops — ticket-856."""
import pytest

from tessera.services.supervision.superviseur_actions import deplacement_pur
from tessera.services.supervision.superviseur_decision_blocs import blocs_proposes, cible_de, deplacer_bloc, retirer_bloc, retrait_pur, sections_nommees

_REGLE = "- **Un test nomme son cas.**\n  Suite de la règle. (ADR-044)"
_CONTRAINTES = f"""# Contraintes

## Proposées

Intro.

{_REGLE}
- **Seconde règle.** Une ligne.

## Git

- **Ancienne.** Texte.

## Tests

*(codeur)*

- **Vitest.** Texte.
"""


def test_multi_line_block_is_read_whole_with_a_stable_id() -> None:
    [premier, second] = blocs_proposes(_CONTRAINTES, "regle")

    assert premier.texte == _REGLE and second.texte == "- **Seconde règle.** Une ligne."
    assert premier.cible == cible_de("regle", _REGLE) and premier.cible.startswith("regle-")
    # L'identifiant suit le texte, pas la place ni la mise en forme.
    assert cible_de("regle", "- **Un test  nomme son cas.**\n  Suite de la règle. (ADR-044)") == premier.cible


def test_no_proposed_section_gives_no_block() -> None:
    assert blocs_proposes("# T\n\n## Git\n\n- **Ancienne.** Texte.\n", "regle") == []


def test_sections_exclude_the_proposed_one_and_keep_their_case() -> None:
    assert sections_nommees(_CONTRAINTES) == ["Git", "Tests"]


def test_moved_block_lands_at_the_end_of_its_section_and_the_move_is_pure() -> None:
    [premier, _] = blocs_proposes(_CONTRAINTES, "regle")

    apres = deplacer_bloc(_CONTRAINTES, "regle", premier.cible, "## Git")

    assert "- **Ancienne.** Texte.\n" + _REGLE in apres
    assert deplacement_pur(_CONTRAINTES, apres, premier.texte, "Git")
    assert [b.texte for b in blocs_proposes(apres, "regle")] == ["- **Seconde règle.** Une ligne."]


def test_moved_block_stays_universal_before_a_role_marker() -> None:
    [premier, _] = blocs_proposes(_CONTRAINTES, "regle")

    apres = deplacer_bloc(_CONTRAINTES, "regle", premier.cible, "Tests")

    assert apres.index(_REGLE) < apres.index("*(codeur)*") < apres.index("- **Vitest.**")
    assert deplacement_pur(_CONTRAINTES, apres, premier.texte, "Tests")


def test_dropped_block_leaves_everything_else_in_place() -> None:
    [premier, _] = blocs_proposes(_CONTRAINTES, "regle")

    apres = retirer_bloc(_CONTRAINTES, "regle", premier.cible)

    assert _REGLE not in apres and "Seconde règle" in apres
    assert retrait_pur(_CONTRAINTES, apres, premier.texte)
    assert not retrait_pur(_CONTRAINTES, apres.replace("Ancienne", "Autre"), premier.texte)


def test_crlf_file_stays_crlf() -> None:
    avant = _CONTRAINTES.replace("\n", "\r\n")
    [premier, _] = blocs_proposes(avant, "regle")

    apres = deplacer_bloc(avant, "regle", premier.cible, "Git")

    assert "\r\n" in apres and "\n" not in apres.replace("\r\n", "")
    assert apres.endswith("\r\n")


@pytest.mark.parametrize("vers", ["Inconnue", "## Proposées", ""])
def test_unknown_target_section_or_block_raises(vers: str) -> None:
    [premier, _] = blocs_proposes(_CONTRAINTES, "regle")

    with pytest.raises(ValueError):
        deplacer_bloc(_CONTRAINTES, "regle", premier.cible, vers)
    with pytest.raises(ValueError):
        retirer_bloc(_CONTRAINTES, "regle", "regle-00000000")
