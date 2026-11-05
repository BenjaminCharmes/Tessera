"""The supervisor's closed action registry and its guards (ticket-851)."""
import pytest

from tessera.services.supervision.superviseur_actions import (
    SCHEMA_DECISION,
    Action,
    Decision,
    chemins_permis,
    deplacement_pur,
    est_sensible,
    lire_decision,
    refus_de_chemin,
)

BON = {"action": "trier", "cible": "ticket-860", "verdict": "agir", "raison": "Ticket brut."}


def test_valid_decision_is_read() -> None:
    assert lire_decision(BON) == Decision(Action.TRIER, "ticket-860", "agir", "Ticket brut.")


def test_decision_ignores_extra_fields() -> None:
    assert lire_decision({**BON, "titre": "Autre"}).cible == "ticket-860"


@pytest.mark.parametrize(
    "brut",
    [
        None,
        "trier",
        [BON],
        {"action": "trier", "cible": "x", "verdict": "agir"},
        {**BON, "cible": ""},
        {**BON, "cible": 12},
        {**BON, "verdict": "peut-etre"},
        {**BON, "raison": "x" * 301},
        {**BON, "raison": None},
    ],
)
def test_decision_off_schema_is_refused(brut: object) -> None:
    with pytest.raises(ValueError):
        lire_decision(brut)


def test_decision_with_a_raison_of_300_characters_is_accepted() -> None:
    assert len(lire_decision({**BON, "raison": "x" * 300}).raison) == 300


@pytest.mark.parametrize("action", ["merger", "supprimer", "", "TRIER"])
def test_unknown_action_is_refused(action: object) -> None:
    with pytest.raises(ValueError, match="registre"):
        lire_decision({**BON, "action": action})


def test_schema_lists_the_four_actions_and_the_required_fields() -> None:
    assert SCHEMA_DECISION["properties"]["action"]["enum"] == [a.value for a in Action]
    assert set(SCHEMA_DECISION["required"]) == {"action", "cible", "verdict", "raison"}
    assert SCHEMA_DECISION["properties"]["raison"]["maxLength"] == 300


@pytest.mark.parametrize("numero", ["027", "031", "037", "039", "053", "055", "067", "073", "080"])
def test_sensitive_text_is_flagged_for_each_door(numero: str) -> None:
    assert est_sensible(f"Une règle neutre. (ADR-{numero})")


@pytest.mark.parametrize("ecriture", ["ADR 27", "adr-0031", "(ADR-006, 031)", "ADR-006 et 073"])
def test_sensitive_text_is_flagged_for_other_spellings_of_a_door(ecriture: str) -> None:
    assert est_sensible(f"Règle ({ecriture}).")


@pytest.mark.parametrize(
    "mot",
    ["secret", "Jeton", "budget", "quota", "suppression", "supprimer", "professionnel",
     "professional", "forcé", "force", "le superviseur", "Superviseur"],
)
def test_sensitive_text_is_flagged_for_each_word(mot: str) -> None:
    assert est_sensible(f"Quand on touche à {mot}, il faut relire.")


@pytest.mark.parametrize(
    "texte",
    ["Quand un test échoue, relire le diff. (ADR-006)", "Rien à signaler (ADR-270, ADR-1027)", ""],
)
def test_neutral_text_is_not_flagged(texte: str) -> None:
    assert not est_sensible(texte)


def test_permitted_paths_per_action() -> None:
    assert chemins_permis(Action.TRIER) == ("tickets/**",)
    assert chemins_permis(Action.DECIDER) == (
        "memory/lecons.md", "memory/contraintes.md", "memory/supervision.md",
    )
    assert chemins_permis(Action.RECONFIER_PR) == ()
    assert chemins_permis(Action.RELANCER_FILE) == ()


def test_path_guard_accepts_the_permitted_paths() -> None:
    assert refus_de_chemin(["tickets/todo/ticket-9.md", "tickets/a/b.md"], Action.TRIER) is None
    assert refus_de_chemin(["memory/lecons.md", "memory/supervision.md"], Action.DECIDER) is None
    assert refus_de_chemin([], Action.RECONFIER_PR) is None


@pytest.mark.parametrize(
    "chemin",
    ["agents.json", "sous/agents.json", ".github/workflows/ci.yml", "CLAUDE.md", "docs/CLAUDE.md",
     ".claude/settings.json", ".claude/settings.local.json", ".git/config", ".git",
     "memory/decisions.md"],
)
@pytest.mark.parametrize("action", [Action.TRIER, Action.DECIDER])
def test_path_guard_refuses_agents_json_github_claude_md_and_git(chemin: str, action: Action) -> None:
    assert refus_de_chemin([chemin], action) is not None


def test_path_guard_refuses_a_path_outside_the_permitted_ones() -> None:
    assert refus_de_chemin(["backend/app.py"], Action.TRIER) is not None
    assert refus_de_chemin(["tickets/x.md"], Action.DECIDER) is not None
    assert refus_de_chemin(["tickets/x.md"], Action.RELANCER_FILE) is not None
    assert refus_de_chemin(["tickets"], Action.TRIER) is not None


@pytest.mark.parametrize(
    "chemin",
    ["tickets/../agents.json", "tickets\\..\\agents.json", "tickets/../.git/HEAD",
     "memory\\decisions.md", "memory/./decisions.md", "tickets/x/../../CLAUDE.md",
     "../autre/tickets/x.md", "/tickets/x.md", "C:\\p\\tickets\\x.md"],
)
def test_path_guard_normalises_dotdot_and_backslashes(chemin: str) -> None:
    assert refus_de_chemin([chemin], Action.TRIER) is not None


def test_path_guard_resolves_dotdot_to_a_permitted_path() -> None:
    assert refus_de_chemin(["memory/../tickets\\todo\\t.md"], Action.TRIER) is None
    assert refus_de_chemin(["memory\\lecons.md"], Action.DECIDER) is None


def test_path_guard_names_the_first_offender() -> None:
    reponse = refus_de_chemin(["tickets/ok.md", "agents.json", "x.py"], Action.TRIER)
    assert reponse is not None and "agents.json" in reponse


AVANT = (
    "# Leçons\n\n## Proposées\n- Quand a, b. (source : ticket-1)\n"
    "- Quand c, d. (source : ticket-2)\n\n## En vigueur\n- Quand e, f.\n"
)
BLOC = "- Quand a, b. (source : ticket-1)"


def test_pure_move_accepts_a_block_moved_and_nothing_else() -> None:
    apres = (
        "# Leçons\n\n## Proposées\n- Quand c, d. (source : ticket-2)\n\n"
        "## En vigueur\n- Quand e, f.\n- Quand a, b. (source : ticket-1)\n"
    )
    assert deplacement_pur(AVANT, apres, BLOC, "## En vigueur")
    assert deplacement_pur(AVANT, apres, BLOC + "\n", "En vigueur")


def test_pure_move_accepts_a_multi_line_block_to_a_named_section() -> None:
    avant = "## Proposées\n\n- **Règle.**\n  suite. (ADR-1)\n- Autre.\n\n## Git\n- Vieille.\n"
    apres = "## Proposées\n\n- Autre.\n\n## Git\n- Vieille.\n- **Règle.**\n  suite. (ADR-1)\n"
    assert deplacement_pur(avant, apres, "- **Règle.**\n  suite. (ADR-1)", "## Git")


def test_pure_move_accepts_a_block_emptying_the_section_and_a_blank_line_more() -> None:
    avant = "## Proposées\n- Seule.\n\n## En vigueur\n- E.\n"
    apres = "## Proposées\n\n## En vigueur\n- E.\n\n- Seule.\n"
    assert deplacement_pur(avant, apres, "- Seule.", "## En vigueur")


def test_pure_move_refuses_an_edited_block_or_extra_line() -> None:
    edite = AVANT.replace("- Quand a, b. (source : ticket-1)\n", "", 1).replace(
        "- Quand e, f.\n", "- Quand e, f.\n- Quand a, b! (source : ticket-1)\n"
    )
    assert not deplacement_pur(AVANT, edite, BLOC, "## En vigueur")
    base = (
        "# Leçons\n\n## Proposées\n- Quand c, d. (source : ticket-2)\n\n"
        "## En vigueur\n- Quand e, f.\n- Quand a, b. (source : ticket-1)\n"
    )
    assert deplacement_pur(AVANT, base, BLOC, "## En vigueur")
    assert not deplacement_pur(AVANT, base + "- Une ligne de plus.\n", BLOC, "## En vigueur")
    assert not deplacement_pur(AVANT, base.replace("Quand e, f.", "Quand e, g."), BLOC, "## En vigueur")


@pytest.mark.parametrize("cas", ["copie", "mauvaise_section", "absent", "meme_section", "titre", "crlf"])
def test_pure_move_refuses_a_move_that_is_not_pure(cas: str) -> None:
    deplace = (
        "# Leçons\n\n## Proposées\n- Quand c, d. (source : ticket-2)\n\n"
        "## En vigueur\n- Quand e, f.\n- Quand a, b. (source : ticket-1)\n"
    )
    cibles = {
        "copie": (AVANT.replace("## En vigueur", "- Quand a, b. (source : ticket-1)\n## En vigueur"), BLOC, "## En vigueur"),
        "mauvaise_section": (deplace, BLOC, "## Autre"),
        "absent": (deplace, "- Quand z, z.", "## En vigueur"),
        "meme_section": (AVANT, BLOC, "## Proposées"),
        "titre": (deplace, "## En vigueur", "## En vigueur"),
        "crlf": (deplace.replace("\n", "\r\n"), BLOC, "## En vigueur"),
    }
    apres, bloc, vers = cibles[cas]
    assert not deplacement_pur(AVANT, apres, bloc, vers)


def test_pure_move_refuses_a_partial_block_of_a_multi_line_rule() -> None:
    avant = "## Proposées\n- **Règle.**\n  suite.\n\n## En vigueur\n- E.\n"
    apres = "## Proposées\n  suite.\n\n## En vigueur\n- E.\n- **Règle.**\n"
    assert not deplacement_pur(avant, apres, "- **Règle.**", "## En vigueur")
