import asyncio
from pathlib import Path

from tessera.models.agent import AgentConfig, AgentPipelineConfig
from tessera.models.project import Project, ProjectCreate
from tessera.services.projets.artifacts import default_mode_for
from tessera.services.projets.extraction_claude_md import lire_readme, parse_active_agents, parse_description, parse_name, parse_stack
from tessera.services.projets.forge import parse_remote
from tessera.services.projets.gabarits_projet import default_agents_json, default_claude_md
from tessera.services.projets.manifeste import lire_chaine, lire_liste, lire_valeur

# Ré-exports : ces noms vivaient ici avant le ticket-691 et des appelants (les
# tests, notamment) les importent encore depuis ce module.
from tessera.services.projets.manifeste_ecriture import AgentAbsentDuProjet as AgentAbsentDuProjet
from tessera.services.projets.manifeste_ecriture import ModeleInconnu as ModeleInconnu
from tessera.services.projets.manifeste_ecriture import set_agent_model as set_agent_model
from tessera.services.projets.manifeste_ecriture import set_agent_provider as set_agent_provider
from tessera.services.projets.manifeste_ecriture import set_pipeline_settings as set_pipeline_settings
from tessera.services.providers.declaration import verifier_configs, verifier_entrees
from tessera.services.providers.noms import PROVIDERS_CONNUS
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

# Ancien nom du générateur, importé par les tests.
_default_agents_json = default_agents_json


# ------------------------------------------------------------------
# Module-level project cache
# Key: (resolved_project_path, claude_md_mtime_ns, claude_md_size, agents_json_mtime_ns, agents_json_size)
# ------------------------------------------------------------------

_ProjectCacheKey = tuple[str, int, int, int, int]
_project_cache: dict[_ProjectCacheKey, Project] = {}


def _stat_key(path: Path) -> tuple[int, int]:
    """Return (mtime_ns, size) for `path`, or (0, 0) if it does not exist."""
    try:
        s = path.stat()
        return s.st_mtime_ns, s.st_size
    except OSError:
        return 0, 0


def _project_cache_key(project_path: Path) -> _ProjectCacheKey:
    """Build a cache key from the project directory's two key files."""
    resolved = str(project_path.resolve())
    cm_mtime, cm_size = _stat_key(project_path / "CLAUDE.md")
    aj_mtime, aj_size = _stat_key(project_path / "agents.json")
    return resolved, cm_mtime, cm_size, aj_mtime, aj_size


# ------------------------------------------------------------------
# Module-level helpers (conservés pour les tests existants)
# ------------------------------------------------------------------


def load_project(project_path: Path) -> Project:
    """Charge un projet depuis son chemin absolu."""
    if not project_path.is_dir():
        raise ValueError(f"Dossier introuvable : {project_path}")

    key = _project_cache_key(project_path)
    if key in _project_cache:
        return _project_cache[key]

    raw = ""
    if (claude_md := project_path / "CLAUDE.md").exists():
        raw = claude_md.read_text(encoding="utf-8")

    github_forge, github_slug = _load_github_remote(project_path)
    project = Project(
        id=project_path.name,
        name=parse_name(raw, fallback=project_path.name),
        path=project_path,
        # Une description déclarée l'emporte : quand ni le CLAUDE.md ni le
        # README ne présentent le projet (ticket-399, cartes de projets).
        description=_chaine_declaree(project_path, "description")
        or parse_description(raw, lire_readme(project_path)),
        active_agents=parse_active_agents(raw),
        stack=parse_stack(raw),
        raw_claude_md=raw,
        github_remote=github_slug,
        github_forge=github_forge,
        category=_load_category(project_path),
        fait_tourner_l_ide=fait_tourner_l_ide(project_path),
        avertissements=_avertissements_du_manifeste(project_path),
    )
    _project_cache[key] = project
    return project


def _avertissements_du_manifeste(project_path: Path) -> list[str]:
    """Signale un `project_id` d'`agents.json` qui ne suit pas le dossier.

    Le nom du dossier reste l'identifiant : le manifeste ne le change pas, il
    est seulement signalé (ticket-481). `agents.json` étant interdit aux
    agents, la correction revient à l'humain.
    """
    declare = _chaine_declaree(project_path, "project_id")
    if declare is None or declare == project_path.name:
        return []
    message = (
        f"agents.json déclare project_id « {declare} » mais le dossier "
        f"s'appelle « {project_path.name} » : l'identifiant retenu est "
        f"« {project_path.name} »."
    )
    _logger.warning(
        "project_id_mismatch",
        extra={"folder": project_path.name, "declared": declare},
    )
    return [message]


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
    return _chaine_declaree(project_path, "category")


def _chaine_declaree(project_path: Path, cle: str) -> str | None:
    """Une chaîne non vide déclarée à la racine d'`agents.json`, sinon `None`."""
    valeur = lire_chaine(project_path, cle)
    if valeur is None or not valeur.strip():
        return None
    return valeur.strip()


def _load_github_remote(project_path: Path) -> tuple[str | None, str | None]:
    """Parse github_remote from agents.json into (forge_name, 'owner/repo').

    The raw value is never rewritten (ADR-036 pattern).
    Returns (None, None) when the field is absent, blank, or the file is unreadable.
    """
    value = lire_valeur(project_path, "github_remote")
    return parse_remote(str(value) if value else None)


def load_agents_config(project_path: Path) -> list[AgentConfig]:
    """Lit agents.json et retourne la liste des AgentConfig actifs."""
    brutes = lire_valeur(project_path, "agents")
    if not isinstance(brutes, (list, tuple)):
        return []
    entrees = list(brutes)
    # Un provider mal orthographié, une clé en clair : pas un manifeste
    # illisible. Le refus sort du `try`, sinon le rôle retomberait sur le
    # défaut sans rien dire (tickets 188 et 669).
    verifier_entrees(entrees)
    try:
        configs = [AgentConfig(**a) for a in entrees]
    except Exception:
        return []
    verifier_configs(configs, PROVIDERS_CONNUS)
    return configs


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
    services = lire_liste(project_path, "services") or []
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
    section = lire_valeur(project_path, "pipeline")
    if section is None:
        return AgentPipelineConfig()
    try:
        return AgentPipelineConfig.model_validate(section)
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
        return await asyncio.to_thread(self._sync_list_projects)

    def _sync_list_projects(self) -> list[Project]:
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

        content = body.claude_md_content or default_claude_md(
            body.project_id, body.name, body.active_agents
        )
        (project_path / "CLAUDE.md").write_text(content, encoding="utf-8")

        # Le manifeste est écrit **toujours**, y compris sans `active_agents` :
        # la modale de création n'en envoie aucun, si bien qu'un projet né de
        # l'UI n'en avait pas du tout, et retombait en silence sur un pipeline
        # codeur → reviewer (ticket-105).
        agents_json = default_agents_json(
            body.project_id, body.active_agents, default_mode_for("create")
        )
        (project_path / "agents.json").write_text(agents_json, encoding="utf-8")

        return load_project(project_path)
