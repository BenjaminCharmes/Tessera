"""Writers of a project's `agents.json` — ticket-691.

Split out of `project_loader`: reading a project and rewriting its manifest are
two jobs. The lower-level read/write primitives stay in `services.manifeste`.
"""

from pathlib import Path

from tessera.services.projets.manifeste import (
    chemin_manifeste,
    ecrire_manifeste,
    lire_pour_modifier,
)
from tessera.services.providers.declaration import verifier_entree, verifier_provider
from tessera.services.providers.noms import PROVIDERS_ANTHROPIC, PROVIDERS_CONNUS


class ModeleInconnu(ValueError):
    """Le modèle demandé n'est pas dans la grille tarifaire."""


class AgentAbsentDuProjet(LookupError):
    """Ce projet ne déclare pas cet agent."""


def set_agent_model(project_path: Path, role: str, model: str) -> None:
    """Change le modèle d'un agent dans le `agents.json` **de ce projet**.

    Le modèle est une propriété du projet, pas de l'agent : le même `codeur`
    mérite un modèle lourd sur un backend métier et un modèle léger sur un
    script personnel. C'est pour cela que ce réglage vit ici et non dans le
    registre d'agents, qui est global (ticket-080).

    Le fichier est réécrit en préservant tout ce qu'il contient d'autre : il
    porte aussi le mode des artefacts, la racine git et la configuration du
    pipeline.
    """
    from tessera.services.cost_calculator import modeles_connus

    data, agent = _entree_du_role(project_path, role)
    # La grille tarifaire ne borne que les providers Anthropic : ailleurs le
    # coût est rapporté par le provider ou nul, et la liste n'aurait rien à
    # dire (ticket-188).
    if agent.get("provider", "agent_sdk") in PROVIDERS_ANTHROPIC and model not in modeles_connus():
        raise ModeleInconnu(
            f"Modèle inconnu : {model}. L'application ne saurait pas en "
            "calculer le coût."
        )
    agent["model"] = model
    _ecrire_manifeste(project_path, data)


def set_agent_provider(
    project_path: Path,
    role: str,
    provider: str,
    fallback: dict[str, str] | None,
) -> None:
    """Change le provider d'un rôle et son repli, dans le manifeste du projet
    (ticket-188). `fallback=None` retire le repli."""
    verifier_provider(role, provider, PROVIDERS_CONNUS)
    if fallback is not None:
        verifier_provider(role, fallback["provider"], PROVIDERS_CONNUS, repli=True)
    data, agent = _entree_du_role(project_path, role)
    # `openai_compatible` sans `base_url` donnerait un manifeste refusé au
    # chargement : refus avant d'écrire (ticket-669).
    verifier_entree(role, {**agent, "provider": provider})
    agent["provider"] = provider
    if fallback is None:
        agent.pop("fallback", None)
    else:
        agent["fallback"] = {"provider": fallback["provider"], "model": fallback["model"]}
    _ecrire_manifeste(project_path, data)


def set_pipeline_settings(
    project_path: Path,
    *,
    pipeline: dict[str, object],
    racine: dict[str, object],
    retirer: tuple[str, ...] = (),
) -> None:
    """Réécrit les seuls réglages reçus dans le manifeste du projet (ticket-196).

    `pipeline` va sous la clef `pipeline`, `racine` au premier niveau
    (`autonomy`, `merge_without_ci`, `category`) ; `retirer` nomme les clefs
    de la racine à supprimer (ticket-398). Tout le reste du fichier est
    préservé : services, artefacts, racine git, agents.
    """
    if not chemin_manifeste(project_path).is_file():
        raise AgentAbsentDuProjet(f"{project_path.name} n'a pas de manifeste")
    data = lire_pour_modifier(project_path)
    section = data.get("pipeline")
    if not isinstance(section, dict):
        section = {}
    section.update(pipeline)
    data["pipeline"] = section
    data.update(racine)
    for clef in retirer:
        data.pop(clef, None)
    _ecrire_manifeste(project_path, data)


def _entree_du_role(project_path: Path, role: str) -> tuple[dict[str, object], dict[str, object]]:
    if not chemin_manifeste(project_path).is_file():
        raise AgentAbsentDuProjet(f"{project_path.name} ne déclare aucun agent")

    data = lire_pour_modifier(project_path)
    agents = data.get("agents", [])
    for agent in agents if isinstance(agents, list) else []:
        if isinstance(agent, dict) and agent.get("role") == role:
            return data, agent
    raise AgentAbsentDuProjet(f"L'agent '{role}' n'est pas déclaré ici")


def _ecrire_manifeste(project_path: Path, data: dict[str, object]) -> None:
    """Réécrit `agents.json` en préservant tout ce qu'il contient d'autre :
    le mode des artefacts, la racine git, la configuration du pipeline."""
    ecrire_manifeste(project_path, data)
