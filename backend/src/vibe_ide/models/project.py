from pathlib import Path

from pydantic import BaseModel, Field

from vibe_ide.models.agent import AgentConfig
from vibe_ide.models.ticket import Ticket


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
