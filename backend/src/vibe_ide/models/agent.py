from enum import Enum

from pydantic import BaseModel, Field


class AgentRole(str, Enum):
    orchestrateur = "orchestrateur"
    codeur = "codeur"
    reviewer = "reviewer"
    architect = "architect"


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


class AgentRunRequest(BaseModel):
    project_id: str
    ticket_id: str
    role: AgentRole


class AgentRunResult(BaseModel):
    ticket_id: str
    role: AgentRole
    success: bool
    output: str = ""
    error: str = Field(default="")
