"""Default files written for a project created by the IDE — ticket-691.

Split out of `project_loader`: the `CLAUDE.md` and `agents.json` templates.
"""

import json

from tessera.services.modeles_par_defaut import modele_par_defaut

#: Les rôles posés quand la création n'en demande aucun. La modale n'envoie que
#: l'identifiant, le nom et la description : sans ce défaut, le projet naissait
#: sans manifeste du tout.
_ROLES_PAR_DEFAUT = ["codeur", "reviewer"]

#: Rôles qui reçoivent le skill de design d'interface (ticket-294).
_ROLES_AVEC_SKILL_DESIGN = {"codeur", "architect"}


def default_claude_md(project_id: str, name: str, active_agents: list[str]) -> str:
    """The `CLAUDE.md` of a new project: title, agents block, empty stack."""
    agents_block = (
        "\n".join(f"- `{a}` — à configurer" for a in active_agents)
        if active_agents
        else "_Aucun agent configuré._"
    )
    return f"""# {name}

Projet créé via Tessera.

---

## Agents actifs sur ce projet

{agents_block}

## Stack

À définir.
"""


def default_agents_json(
    project_id: str, active_agents: list[str], artifacts: str
) -> str:
    """Le manifeste d'un projet neuf, écrit en entier plutôt que deviné.

    Sans manifeste, `load_pipeline_config` rend un `AgentPipelineConfig()` où
    la sécurité et le validateur sont éteints — alors que les deux services
    sont déjà câblés. Ils l'étaient par absence de déclaration, pas par choix,
    et rien ne le disait.

    `max_instances` n'est plus écrit : rien ne le lit, le backend ne contient
    aucun `asyncio.gather` et le pipeline est strictement séquentiel. C'est le
    défaut que ticket-091 a nettoyé sur `auto_merge_on_approve` — un réglage
    qu'on lit et qu'on croit.
    """
    roles = active_agents or _ROLES_PAR_DEFAUT
    agents = [
        {
            "role": role,
            "model": modele_par_defaut(role),
            "max_tokens": 8192 if role == "codeur" else 4096,
            "prompt_file": f"agents/prompts/{role}.md",
            "active": True,
            **({"skills": ["tessera:design-ui"]} if role in _ROLES_AVEC_SKILL_DESIGN else {}),
        }
        for role in roles
    ]
    data = {
        "project_id": project_id,
        # Explicite plutôt que dépendant du défaut de lecture d'ADR-023, qui
        # échoue fermé : un manifeste muet et un manifeste qui a choisi `local`
        # se lisent pareil, et seul le second l'a décidé.
        "artifacts": artifacts,
        # ADR-029 : le défaut protège. On n'écrit jamais `merge` dans un
        # fichier généré — merger, c'est décider qu'un travail est bon.
        "autonomy": "commit",
        "agents": agents,
        "pipeline": {
            "max_review_rounds": 3,
            # Un flag à vrai sans commande valide est pire qu'un flag à faux :
            # le lanceur avale l'erreur et rend `True`, si bien que l'absence
            # de tests se lirait comme des tests verts. Un projet neuf n'a pas
            # de stack, donc aucune commande ne se devine ici.
            "testeur_enabled": False,
            "test_command": None,
            "securite_enabled": True,
            "validateur_enabled": True,
        },
    }
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"
