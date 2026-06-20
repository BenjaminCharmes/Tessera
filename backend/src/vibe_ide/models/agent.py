from enum import Enum

from pydantic import BaseModel, Field


class AgentRole(str, Enum):
    orchestrateur = "orchestrateur"
    codeur = "codeur"
    reviewer = "reviewer"
    architect = "architect"


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
