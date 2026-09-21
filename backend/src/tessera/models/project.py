from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from tessera.models.agent import AgentConfig
from tessera.models.ticket import Ticket, TicketDraft, TicketDraftPlan


class Project(BaseModel):
    id: str = Field(description="Nom du dossier projet, ex: ide-core")
    name: str
    path: Path
    description: str = ""
    active_agents: list[str] = Field(default_factory=list)
    stack: str | None = None
    raw_claude_md: str = ""
    github_remote: str | None = None


class ProjectCreate(BaseModel):
    project_id: str
    name: str
    active_agents: list[str] = Field(default_factory=list)
    claude_md_content: str = ""


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
