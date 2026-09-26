import json
import re
from pathlib import Path

from tessera.models.agent import AgentConfig, AgentPipelineConfig
from tessera.models.project import Project, ProjectCreate
from tessera.services.artifacts import default_mode_for
from tessera.services.providers.noms import (
    PROVIDERS_ANTHROPIC,
    PROVIDERS_CONNUS,
    ProviderInconnu,
)


# ------------------------------------------------------------------
# Module-level helpers (conservés pour les tests existants)
# ------------------------------------------------------------------


def load_project(project_path: Path) -> Project:
    """Charge un projet depuis son chemin absolu."""
    if not project_path.is_dir():
        raise ValueError(f"Dossier introuvable : {project_path}")

    raw = ""
    if (claude_md := project_path / "CLAUDE.md").exists():
        raw = claude_md.read_text(encoding="utf-8")

    return Project(
        id=project_path.name,
        name=_parse_name(raw, fallback=project_path.name),
        path=project_path,
        description=_parse_description(raw),
        active_agents=_parse_active_agents(raw),
        stack=_parse_stack(raw),
        raw_claude_md=raw,
        github_remote=_load_github_remote(project_path),
        category=_load_category(project_path),
        fait_tourner_l_ide=fait_tourner_l_ide(project_path),
    )


def list_projects(workspace: Path) -> list[Project]:
    """Liste tous les sous-dossiers d'un workspace (sans filtrer sur CLAUDE.md)."""
    if not workspace.is_dir():
        return []
    return [
        load_project(p)
        for p in sorted(workspace.iterdir())
        if p.is_dir() and not p.name.startswith(".")
    ]


def _load_category(project_path: Path) -> str | None:
    """La catégorie déclarée, `None` si absente, illisible, mal typée ou vide.

    Une catégorie vide vaudrait un groupe sans nom à l'écran ; mieux vaut
    ranger le projet avec ceux qui ne déclarent rien.
    """
    agents_json = project_path / "agents.json"
    if not agents_json.exists():
        return None
    try:
        data = json.loads(agents_json.read_text(encoding="utf-8"))
    except Exception:
        return None
    valeur = data.get("category")
    if not isinstance(valeur, str) or not valeur.strip():
        return None
    return valeur.strip()


def _load_github_remote(project_path: Path) -> str | None:
    agents_json = project_path / "agents.json"
    if not agents_json.exists():
        return None
    try:
        data = json.loads(agents_json.read_text(encoding="utf-8"))
        value = data.get("github_remote")
        return str(value) if value else None
    except Exception:
        return None


def load_agents_config(project_path: Path) -> list[AgentConfig]:
    """Lit agents.json et retourne la liste des AgentConfig actifs."""
    agents_json = project_path / "agents.json"
    if not agents_json.exists():
        return []
    try:
        data = json.loads(agents_json.read_text(encoding="utf-8"))
        configs = [AgentConfig(**a) for a in data.get("agents", [])]
    except Exception:
        return []
    # Un provider mal orthographié n'est pas un manifeste illisible : le
    # taire enverrait le rôle sur le défaut sans rien dire (ticket-188).
    for config in configs:
        _verifier_provider(config.role, config.provider)
        if config.fallback is not None:
            _verifier_provider(config.role, config.fallback.provider, repli=True)
    return configs


def _verifier_provider(role: str, provider: str, repli: bool = False) -> None:
    if provider in PROVIDERS_CONNUS:
        return
    quoi = "repli" if repli else "provider"
    raise ProviderInconnu(
        f"Rôle '{role}' : {quoi} inconnu {provider!r}. "
        f"Valeurs acceptées : {', '.join(PROVIDERS_CONNUS)}."
    )


def fait_tourner_l_ide(
    project_path: Path, racine_de_l_ide: Path | None = None
) -> bool:
    """Ce projet est-il celui qui exécute l'IDE en ce moment ? — ticket-152.

    C'est le cas du projet bootstrap d'ADR-001 : il construit l'IDE, donc il
    travaille dans le dépôt qui le contient — celui-là même dont le backend
    est issu. Lui proposer « Lancer » démarrerait un second backend sur un
    port déjà pris, et le cas utile n'existe pas : il faut que l'IDE tourne
    pour qu'on voie le bouton.

    La reconnaissance passe par `racine_autorisee` (ADR-028), pas par le nom
    du projet : un projet peut s'appeler autrement, et un projet client qui
    déclare `git_root: ancestor` pointe vers **son** dépôt, pas celui-ci.

    Les deux côtés sont résolus, liens symboliques compris — un projet
    importé par symlink serait sinon reconnu à tort.
    """
    from tessera.config import _REPO_ROOT
    from tessera.services.providers.perimetre import racine_autorisee

    racine = (racine_de_l_ide or _REPO_ROOT).resolve()
    try:
        return racine_autorisee(project_path).resolve() == racine
    except OSError:
        return False


def load_services_config(project_path: Path) -> list[dict[str, str]]:
    """Les services déclarés dans `agents.json`, ou rien — ticket-137.

    ADR-042 : la commande se déclare, elle ne se devine pas. Une liste vide
    n'est donc pas un manque à combler par une heuristique, c'est la réponse
    « ce projet ne se lance pas depuis l'IDE ».
    """
    agents_json = project_path / "agents.json"
    if not agents_json.exists():
        return []
    try:
        data = json.loads(agents_json.read_text(encoding="utf-8"))
    except Exception:
        return []
    services = data.get("services") or []
    if not isinstance(services, list):
        return []
    return [
        {
            "nom": str(s.get("nom", "")),
            "commande": str(s.get("commande", "")),
            "cwd": str(s.get("cwd", "") or ""),
        }
        for s in services
        if isinstance(s, dict) and s.get("nom") and s.get("commande")
    ]


def load_pipeline_config(project_path: Path) -> AgentPipelineConfig:
    """Lit la section pipeline de agents.json."""
    agents_json = project_path / "agents.json"
    if not agents_json.exists():
        return AgentPipelineConfig()
    try:
        data = json.loads(agents_json.read_text(encoding="utf-8"))
        return AgentPipelineConfig(**data.get("pipeline", {}))
    except Exception:
        return AgentPipelineConfig()


# ------------------------------------------------------------------
# ProjectLoader — API async pour l'orchestrateur
# ------------------------------------------------------------------


class ProjectLoader:
    """Façade async autour du workspace. Filtre les projets sans CLAUDE.md."""

    def __init__(self, workspace_dir: Path) -> None:
        self._workspace = workspace_dir

    async def list_projects(self) -> list[Project]:
        if not self._workspace.is_dir():
            return []
        projects: list[Project] = []
        for p in sorted(self._workspace.iterdir()):
            if p.is_dir() and not p.name.startswith(".") and (p / "CLAUDE.md").exists():
                try:
                    projects.append(load_project(p))
                except Exception:
                    continue
        return projects

    async def load_project(self, project_id: str) -> Project:
        return load_project(self._workspace / project_id)

    async def create_project(self, body: ProjectCreate) -> Project:
        project_path = self._workspace / body.project_id
        if project_path.exists():
            raise ValueError(f"Projet déjà existant : {body.project_id}")

        for subdir in [
            "tickets/todo",
            "tickets/in-progress",
            "tickets/done",
            "tickets/cancelled",
            "memory",
            "workspace",
        ]:
            (project_path / subdir).mkdir(parents=True, exist_ok=True)

        content = body.claude_md_content or _default_claude_md(
            body.project_id, body.name, body.active_agents
        )
        (project_path / "CLAUDE.md").write_text(content, encoding="utf-8")

        # Le manifeste est écrit **toujours**, y compris sans `active_agents` :
        # la modale de création n'en envoie aucun, si bien qu'un projet né de
        # l'UI n'en avait pas du tout, et retombait en silence sur un pipeline
        # codeur → reviewer (ticket-105).
        agents_json = _default_agents_json(
            body.project_id, body.active_agents, default_mode_for("create")
        )
        (project_path / "agents.json").write_text(agents_json, encoding="utf-8")

        return load_project(project_path)


# ------------------------------------------------------------------
# Parsers et templates internes
# ------------------------------------------------------------------


#: `CLAUDE.md` accolé au titre, avant ou après un tiret. Les prompts qui
#: génèrent ces fichiers écrivent « # CLAUDE.md — NomDuProjet », ce qui est un
#: bon en-tête de fichier et un mauvais nom de projet.
_DECORATION = re.compile(
    r"^\s*CLAUDE\.md\s*$"                       # le titre n'est que le fichier
    r"|^\s*CLAUDE\.md\s*[—:–-]\s*(?:projet\s+)?"  # « CLAUDE.md — projet X »
    r"|\s*[—:–-]\s*CLAUDE\.md\s*$",              # « X — CLAUDE.md »
    re.IGNORECASE,
)


def _parse_name(content: str, fallback: str) -> str:
    """Le nom lisible du projet, tiré du premier titre du CLAUDE.md (ADR-007).

    Le titre sert deux choses à la fois : il annonce le fichier et il nomme le
    projet. Les deux ne veulent pas la même chose — la barre latérale affichait
    « Lyra — CLAUDE.md » et « CLAUDE.md — projet ide-core ». Le nom du
    fichier est retiré ici, parce que c'est ici qu'on lit un **nom de projet**
    (ticket-093).
    """
    for line in content.splitlines():
        m = re.match(r"^#\s+(.+)", line)
        if not m:
            continue
        titre = _DECORATION.sub("", m.group(1).strip()).strip()
        return titre or fallback
    return fallback


def _parse_description(content: str) -> str:
    skip_heading = True
    for line in content.splitlines():
        stripped = line.strip()
        if skip_heading and stripped.startswith("#"):
            skip_heading = False
            continue
        if stripped and not stripped.startswith("#"):
            return stripped
    return ""


def _parse_active_agents(content: str) -> list[str]:
    in_section = False
    agents: list[str] = []
    for line in content.splitlines():
        if re.match(r"^##\s+Agents actifs", line):
            in_section = True
            continue
        if in_section and line.startswith("##"):
            break
        if in_section:
            m = re.match(r"^-\s+`(\w+)`", line)
            if m:
                agents.append(m.group(1))
    return agents


def _parse_stack(content: str) -> str | None:
    in_section = False
    lines: list[str] = []
    for line in content.splitlines():
        if re.match(r"^##\s+Stack", line):
            in_section = True
            continue
        if in_section and line.startswith("##"):
            break
        if in_section and line.strip():
            lines.append(line.strip())
    return "\n".join(lines) if lines else None


def _default_claude_md(project_id: str, name: str, active_agents: list[str]) -> str:
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


#: Les rôles posés quand la création n'en demande aucun. La modale n'envoie que
#: l'identifiant, le nom et la description : sans ce défaut, le projet naissait
#: sans manifeste du tout.
_ROLES_PAR_DEFAUT = ["codeur", "reviewer"]


def _default_agents_json(
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
            "model": "claude-sonnet-4-6",
            "max_tokens": 8192 if role == "codeur" else 4096,
            "prompt_file": f"agents/prompts/{role}.md",
            "active": True,
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
    _verifier_provider(role, provider)
    if fallback is not None:
        _verifier_provider(role, fallback["provider"], repli=True)
    data, agent = _entree_du_role(project_path, role)
    agent["provider"] = provider
    if fallback is None:
        agent.pop("fallback", None)
    else:
        agent["fallback"] = {"provider": fallback["provider"], "model": fallback["model"]}
    _ecrire_manifeste(project_path, data)


def _entree_du_role(project_path: Path, role: str) -> tuple[dict[str, object], dict[str, object]]:
    agents_json = project_path / "agents.json"
    if not agents_json.is_file():
        raise AgentAbsentDuProjet(f"{project_path.name} ne déclare aucun agent")

    data = json.loads(agents_json.read_text(encoding="utf-8"))
    for agent in data.get("agents", []):
        if agent.get("role") == role:
            return data, agent
    raise AgentAbsentDuProjet(f"L'agent '{role}' n'est pas déclaré ici")


def _ecrire_manifeste(project_path: Path, data: dict[str, object]) -> None:
    """Réécrit `agents.json` en préservant tout ce qu'il contient d'autre :
    le mode des artefacts, la racine git, la configuration du pipeline."""
    (project_path / "agents.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
