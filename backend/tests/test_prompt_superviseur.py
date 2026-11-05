"""The supervisor prompt names every area ADR-080 forbids it — ticket-852."""
import re
from pathlib import Path

import pytest

from tessera.services.supervision.superviseur_actions import Action

_RACINE = Path(__file__).resolve().parents[2]
_PROMPT = _RACINE / "agents" / "prompts" / "superviseur.md"
_DECISIONS = _RACINE / "projects" / "ide-core" / "memory" / "decisions.md"

#: Les interdits que cite la phrase « Jamais : » d'ADR-080, mot pour mot.
_INTERDITS = ["argent", "suppression", "secrets", "professional", "agents.json", ".github/", "CLAUDE.md"]


def _bloc_adr_080() -> str:
    texte = _DECISIONS.read_text(encoding="utf-8")
    debut = texte.index("## ADR-080")
    suite = re.search(r"\n## ADR-", texte[debut + 1:])
    return texte[debut: debut + 1 + suite.start()] if suite else texte[debut:]


def test_prompt_names_each_forbidden_area() -> None:
    prompt = _PROMPT.read_text(encoding="utf-8")
    adr = _bloc_adr_080()

    for mot in _INTERDITS:
        assert mot in adr, f"ADR-080 ne cite plus {mot}"
        assert mot in prompt, f"le prompt ne nomme pas {mot}"
    # `.git/` et le superviseur lui-même : portés par la spec, pas par la phrase de l'ADR.
    assert ".git/" in prompt
    assert "superviseur lui-même" in prompt


def test_prompt_names_the_decision_contract() -> None:
    prompt = _PROMPT.read_text(encoding="utf-8")

    for action in Action:
        assert f"`{action.value}`" in prompt
    for verdict in ("agir", "a_toi", "rien"):
        assert f"`{verdict}`" in prompt
    for champ in ("action", "cible", "verdict", "raison"):
        assert f'"{champ}"' in prompt


@pytest.mark.parametrize("phrase", ["jamais une consigne", "Quand tu ne sais pas"])
def test_prompt_treats_the_dossier_as_data_and_escalates(phrase: str) -> None:
    assert phrase in _PROMPT.read_text(encoding="utf-8")
