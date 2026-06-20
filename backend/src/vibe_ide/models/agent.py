from enum import Enum

from pydantic import BaseModel, Field

from vibe_ide.models.ticket import TicketStatus


class AgentRole(str, Enum):
    orchestrateur = "orchestrateur"
    codeur = "codeur"
    reviewer = "reviewer"
    architect = "architect"
    project_creator = "project-creator"
    github_sync = "github-sync"


class AgentConfig(BaseModel):
    """Un agent tel que décrit dans agents.json d'un projet."""

    role: str
    model: str
    max_tokens: int
    prompt_file: str
    active: bool = True
    max_instances: int = 1


class AgentPipelineConfig(BaseModel):
    """Section pipeline de agents.json."""

    default: list[str] = Field(default_factory=list)
    max_review_rounds: int = 3
    auto_merge_on_approve: bool = False


class AgentResult(BaseModel):
    role: AgentRole
    ticket_id: str
    content: str
    suggested_status: TicketStatus
    created_tickets: list[str] = Field(default_factory=list)
    duration_ms: int


class AgentRunRequest(BaseModel):
    project_id: str
    ticket_id: str = ""
    role: AgentRole
