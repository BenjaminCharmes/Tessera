"""The guards and the in-place rewriting of the supervisor's triage — ticket-855, ADR-080."""
from pathlib import Path
from typing import Any

import pytest

from tessera.models.ticket import TicketPriority, TicketType
from tessera.services.providers.signaler import LIGNE_CRITERES
from tessera.services.supervision.superviseur_actions import SCHEMA_DECISION
from tessera.services.supervision.superviseur_tri_ecriture import decouper, est_brut, nouveau_corps, reecrire_si_brut, section
from tessera.services.supervision.superviseur_tri_gardes import SCHEMA_TRI, PlanTri, RefusTri, lire_plan

_CORPS = f"## Signalement\n\n- Projet source : x\n\n## Critères d'acceptation\n\n{LIGNE_CRITERES}\n"
_PLAN = PlanTri(
    "A title", TicketType.fix, TicketPriority.high,
    ("The first criterion is checkable", "The second criterion is checkable"), ("ticket-100",), "Not the dialog.",
)


def _brut(**surcharge: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "titre": "A good title", "type": "feat", "priorite": "low",
        "criteres": ["The export of an empty list shows a message"], "depends_on": [], "hors_portee": "",
    }
    return {**base, **surcharge}


def _lire(brut: dict[str, Any], professionnel: bool = False) -> PlanTri:
    return lire_plan(
        brut, existants={"ticket-100", "ticket-200"}, propre_id="ticket-300",
        titre_actuel="Old title", professionnel=professionnel,
    )


def test_schema_extends_the_decision_schema_with_the_triage_fields() -> None:
    assert set(SCHEMA_DECISION["properties"]) < set(SCHEMA_TRI["properties"])
    assert SCHEMA_TRI["required"] == SCHEMA_DECISION["required"]
    assert SCHEMA_TRI["properties"]["titre"]["maxLength"] == 120
    assert "design" in SCHEMA_TRI["properties"]["type"]["enum"]


def test_valid_output_becomes_a_plan() -> None:
    plan = _lire(_brut(criteres=["- [ ] The export of an empty list shows a message"], depends_on=["ticket-100"]))

    assert plan.titre == "A good title" and plan.type is TicketType.feat and plan.priorite is TicketPriority.low
    assert plan.criteres == ("The export of an empty list shows a message",)
    assert plan.depends_on == ("ticket-100",)


@pytest.mark.parametrize(
    "surcharge",
    [
        {"titre": ""}, {"titre": "x" * 121}, {"titre": "two\nlines"}, {"type": "epic"}, {"priorite": "urgent"},
        {"criteres": [f"Criterion number {n} is precise" for n in range(9)]},
        {"criteres": [42]}, {"criteres": "one criterion in a string"},
        {"criteres": ["TODO: write the criteria here"]},
        {"depends_on": ["ticket-300"]}, {"depends_on": ["ticket-404"]}, {"depends_on": ["whatever"]},
        {"depends_on": "ticket-100"},
    ],
)
def test_an_off_plan_field_is_refused(surcharge: dict[str, Any]) -> None:
    with pytest.raises(RefusTri):
        _lire(_brut(**surcharge))


def test_missing_field_is_refused() -> None:
    brut = _brut()
    del brut["priorite"]

    with pytest.raises(RefusTri, match="priorite"):
        _lire(brut)


def test_professional_plan_keeps_the_title_and_drops_the_limits() -> None:
    plan = _lire(_brut(titre="Invented detail", hors_portee="More detail"), professionnel=True)

    assert plan.titre == "Old title" and plan.hors_portee == ""


def test_raw_body_is_recognised_and_a_written_one_is_not() -> None:
    assert est_brut(_CORPS)
    assert not est_brut(nouveau_corps(_CORPS, _PLAN))
    assert not est_brut("## Description\n\nNo criteria section.\n")
    assert not est_brut(_CORPS.replace(LIGNE_CRITERES, f"{LIGNE_CRITERES}\n- [ ] A second criterion that is real"))


def test_rewrite_replaces_the_criteria_and_keeps_every_other_section() -> None:
    corps = nouveau_corps(_CORPS, _PLAN)

    assert [titre for titre, _ in decouper(corps)] == [
        "", "signalement", "critères d'acceptation", "ce que ça ne fait pas",
    ]
    assert section(corps, "signalement") == section(_CORPS, "signalement")
    assert LIGNE_CRITERES not in corps and corps.count("- [ ] ") == 2 and corps.endswith("\n")


def test_rewrite_does_not_duplicate_an_existing_limits_section() -> None:
    corps = nouveau_corps(_CORPS + "\n## Ce que ça ne fait pas\n\nAlready there.\n", _PLAN)

    assert corps.count("Ce que ça ne fait pas") == 1 and "Not the dialog." not in corps


def test_rewrite_leaves_a_missing_or_triaged_file_untouched(tmp_path: Path) -> None:
    assert not reecrire_si_brut(tmp_path / "absent.md", _PLAN)
    fichier = tmp_path / "ticket-1-x.md"
    texte = "---\nid: ticket-1\ntitle: T\n---\n## Critères d'acceptation\n\n- [ ] A criterion already written\n"
    fichier.write_text(texte, encoding="utf-8")

    assert not reecrire_si_brut(fichier, _PLAN)
    assert fichier.read_text(encoding="utf-8") == texte
