"""Ce que le dépôt livre ne se supprime pas depuis l'IDE — ticket-079."""
from pathlib import Path

from vibe_ide.services.agent_registry import AgentRegistryService

#: Le dossier des prompts livrés avec le dépôt.
_PROMPTS = Path(__file__).resolve().parents[2] / "agents" / "prompts"


def test_tout_prompt_livre_est_declare_natif() -> None:
    # Panne vecue : `BUILTIN_ROLES` etait une liste ecrite a la main, restee a
    # six roles alors que le depot en livre treize. Sept agents du produit —
    # dont `securite`, `testeur`, `validateur` et `agent-creator` — passaient
    # pour des creations de l'utilisateur, et se supprimaient d'un clic.
    # `agent-creator` a effectivement disparu le 2026-09-17.
    livres = {f.stem for f in _PROMPTS.glob("*.md")}

    non_declares = sorted(livres - AgentRegistryService.BUILTIN_ROLES)

    assert non_declares == [], (
        "ces prompts viennent du dépôt mais sont réputés créés par "
        f"l'utilisateur, donc supprimables : {non_declares}"
    )


def test_aucun_natif_ne_manque_sur_le_disque() -> None:
    # L'inverse : un rôle déclaré natif sans prompt livré promet un agent qui
    # n'existe pas.
    livres = {f.stem for f in _PROMPTS.glob("*.md")}

    manquants = sorted(AgentRegistryService.BUILTIN_ROLES - livres)

    assert manquants == [], f"déclarés natifs mais absents du dépôt : {manquants}"
