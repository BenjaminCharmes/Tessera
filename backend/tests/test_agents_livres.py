"""Ce que le dépôt livre ne se supprime pas depuis l'IDE — ticket-079."""
import json
import re
from pathlib import Path

from tessera.services.agent_registry import AgentRegistryService

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


# ------------------------------------------------------------------
# Ce qui est protégé est ce dont le code dépend — ticket-094
# ------------------------------------------------------------------

_SOURCES = Path(__file__).resolve().parents[1] / "src"


def _roles_charges_par_le_code() -> set[str]:
    """Les prompts que le code charge **par leur nom**.

    C'est la vraie ligne de partage. « Natif » et « personnalisé » disent qui
    a écrit le fichier — ce qui ne change rien, puisque l'agent qui écrit un
    prompt depuis l'IDE est le même que celui qui en livre un avec le dépôt.
    Ce qui compte est ailleurs : si le produit charge `codeur.md` par son nom,
    supprimer ce fichier casse le pipeline ; supprimer un `expert-sql.md` que
    personne ne nomme ne casse rien.
    """
    noms: set[str] = set()
    for fichier in _SOURCES.rglob("*.py"):
        for trouve in re.findall(r"[\"']([a-z][a-z0-9-]*)\.md[\"']", fichier.read_text(encoding="utf-8")):
            noms.add(trouve)
    return noms & {f.stem for f in _PROMPTS.glob("*.md")}


def test_tout_prompt_charge_par_le_code_est_protege() -> None:
    # La panne de ticket-079 recommencerait à l'identique pour un agent
    # ajouté plus tard : la liste est écrite à la main, le code évolue à
    # côté. Ce test dérive la contrainte du code lui-même.
    charges = _roles_charges_par_le_code()

    non_proteges = sorted(charges - AgentRegistryService.BUILTIN_ROLES)

    assert non_proteges == [], (
        "le code charge ces prompts par leur nom, mais ils sont supprimables "
        f"d'un clic depuis l'IDE : {non_proteges}"
    )


def _roles_declares_par_les_projets() -> set[str]:
    """Les prompts qu'un projet livré avec le dépôt déclare dans agents.json."""
    racine = _PROMPTS.parent.parent / "projects"
    declares: set[str] = set()
    for agents_json in racine.glob("*/agents.json"):
        try:
            data = json.loads(agents_json.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        for agent in data.get("agents", []):
            if (role := agent.get("role")):
                declares.add(str(role))
    return declares & {f.stem for f in _PROMPTS.glob("*.md")}


def test_tout_prompt_declare_par_un_projet_est_protege() -> None:
    # Même dérive que ticket-079, par l'autre porte : un agent ajouté pour un
    # projet du dépôt est aussi supprimable d'un clic que les autres, et son
    # projet cesse alors de tourner.
    non_proteges = sorted(
        _roles_declares_par_les_projets() - AgentRegistryService.BUILTIN_ROLES
    )

    assert non_proteges == [], (
        f"des projets du dépôt déclarent ces agents, qui restent supprimables : "
        f"{non_proteges}"
    )
