import json
import re
from pathlib import Path

from vibe_ide.models.agent import AgentConfig, AgentPipelineConfig
from vibe_ide.models.project import Project, ProjectCreate


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
        return [AgentConfig(**a) for a in data.get("agents", [])]
    except Exception:
        return []


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

        if body.active_agents:
            agents_json = _default_agents_json(body.project_id, body.active_agents)
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

Projet créé via vibe-ide.

---

## Agents actifs sur ce projet

{agents_block}

## Stack

À définir.
"""


def _default_agents_json(project_id: str, active_agents: list[str]) -> str:
    agents = [
        {
            "role": role,
            "model": "claude-sonnet-4-6",
            "max_tokens": 8192 if role == "codeur" else 4096,
            "prompt_file": f"agents/prompts/{role}.md",
            "active": True,
            **({"max_instances": 2} if role == "codeur" else {}),
        }
        for role in active_agents
    ]
    data = {
        "project_id": project_id,
        "agents": agents,
        "pipeline": {"max_review_rounds": 3},
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
    from vibe_ide.services.cost_calculator import modeles_connus

    if model not in modeles_connus():
        raise ModeleInconnu(
            f"Modèle inconnu : {model}. L'application ne saurait pas en "
            "calculer le coût."
        )

    agents_json = project_path / "agents.json"
    if not agents_json.is_file():
        raise AgentAbsentDuProjet(f"{project_path.name} ne déclare aucun agent")

    data = json.loads(agents_json.read_text(encoding="utf-8"))
    agents = data.get("agents", [])
    for agent in agents:
        if agent.get("role") == role:
            agent["model"] = model
            break
    else:
        raise AgentAbsentDuProjet(f"L'agent '{role}' n'est pas déclaré ici")

    agents_json.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
