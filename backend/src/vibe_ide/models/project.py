from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from vibe_ide.models.agent import AgentConfig
from vibe_ide.models.ticket import Ticket, TicketDraft


class Project(BaseModel):
    id: str = Field(description="Nom du dossier projet, ex: ide-core")
    name: str
    path: Path
    description: str = ""
    active_agents: list[str] = Field(default_factory=list)
    stack: str | None = None
    raw_claude_md: str = ""


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


class ProjectImport(BaseModel):
    source_path: Path = Field(description="Chemin absolu vers le dossier à importer")
    mode: Literal["copy", "symlink"] = Field(default="symlink")
    project_id: str | None = Field(default=None, description="ID désiré (déduit du nom du dossier si absent)")


class ProjectImportResponse(BaseModel):
    project: Project


class AnalyzeProjectRequest(BaseModel):
    overwrite: bool = False


class AnalysisResult(BaseModel):
    claude_md: str
    detected_stack: list[str]
    suggested_agents: list[str]
    claude_md_written: bool
