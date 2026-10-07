from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from tessera.models.agent import AgentConfig
from tessera.models.ticket import Ticket, TicketDraft, TicketDraftPlan
from tessera.utils.project_id import validate_project_id


class Project(BaseModel):
    id: str = Field(description="Nom du dossier projet, ex: ide-core")
    name: str
    path: Path
    description: str = ""
    active_agents: list[str] = Field(default_factory=list)
    stack: str | None = None
    raw_claude_md: str = ""
    #: Always 'owner/repo' after loading, regardless of the raw form in agents.json.
    github_remote: str | None = None
    #: The forge name derived from github_remote ('GitHub', 'GitLab', …).
    github_forge: str | None = None
    #: Le rangement déclaré dans `agents.json`. Une catégorie se déclare, elle
    #: ne se devine pas : ni le nom du dossier ni l'URL du dépôt ne disent à
    #: quoi sert un projet — c'est le raisonnement d'ADR-042 pour les commandes
    #: de lancement. Sans déclaration, le projet reste visible, rangé à part
    #: (ticket-175).
    category: str | None = None
    #: Ce projet exécute l'IDE en ce moment — le bootstrap d'ADR-001. Lui
    #: proposer « Lancer » démarrerait un second backend sur un port pris, et
    #: le cas utile n'existe pas : il faut que l'IDE tourne pour qu'on voie le
    #: bouton (ticket-152).
    fait_tourner_l_ide: bool = False


def _verifier_project_id(v: str | None) -> str | None:
    """Refuse a project_id that could point outside the projects folder (ticket-370)."""
    if v is not None and not validate_project_id(v):
        raise ValueError(f"project_id invalide : {v!r}")
    return v


class ProjectCreate(BaseModel):
    project_id: str
    name: str
    active_agents: list[str] = Field(default_factory=list)
    claude_md_content: str = ""

    _project_id_valide = field_validator("project_id")(_verifier_project_id)


class ProjectContext(BaseModel):
    project_id: str
    claude_md: str
    active_agents: list[str]
    agent_configs: list[AgentConfig]
    open_tickets: list[Ticket]
    recent_decisions: str


class ConversationMessage(BaseModel):
    role: str
    content: str


class CreateProjectRequest(BaseModel):
    conversation: list[ConversationMessage]


class CreateProjectResponse(BaseModel):
    project: Project | None = None
    suggested_tickets: list[TicketDraft] = Field(default_factory=list)
    claude_md_generated: str = ""
    agent_message: str = ""
    done: bool = False
    agents_created: list[str] = Field(default_factory=list)


class ProjectCreationResult(BaseModel):
    project: Project
    agents_created: list[str] = Field(default_factory=list)
    #: Le projet est-il la racine d'un dépôt git utilisable (ticket-104) ?
    #: Faux quand l'initialisation a échoué — le projet existe alors sur
    #: disque, mais aucun run de pipeline n'y démarrera tant qu'on n'aura pas
    #: rattrapé à la main, `GitWorkspaceService` exigeant un dépôt à la racine
    #: (ADR-024). L'information est rendue plutôt que levée : le projet est
    #: déjà créé, échouer laisserait l'utilisateur avec les deux.
    repository_ready: bool = False


class ProjectImport(BaseModel):
    source_path: Path = Field(description="Chemin absolu vers le dossier à importer")
    mode: Literal["copy", "symlink"] = Field(default="symlink")
    project_id: str | None = Field(default=None, description="ID désiré (déduit du nom du dossier si absent)")

    _project_id_valide = field_validator("project_id")(_verifier_project_id)


class ProjectImportResponse(BaseModel):
    project: Project


class PlanRequest(BaseModel):
    description: str = Field(description="Description de l'évolution en langage naturel")


class PlanResult(BaseModel):
    drafts: list[TicketDraftPlan]
    summary: str


class AnalyzeProjectRequest(BaseModel):
    overwrite: bool = False


class AnalysisResult(BaseModel):
    claude_md: str
    detected_stack: list[str]
    suggested_agents: list[str]
    claude_md_written: bool


class CloneProjectRequest(BaseModel):
    repo_url: str = Field(description="URL HTTPS du repo GitHub, ex: https://github.com/owner/repo")
    project_id: str | None = Field(default=None, description="ID désiré (déduit du nom du repo si absent)")

    _project_id_valide = field_validator("project_id")(_verifier_project_id)


class CloneProjectResponse(BaseModel):
    project: Project
    claude_md_generated: bool
    detected_stack: list[str]


class GithubSyncRequest(BaseModel):
    direction: Literal["pull", "push", "both"] = "pull"


class GithubSyncResult(BaseModel):
    pulled: int
    pushed: int
    skipped: int
