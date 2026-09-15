from enum import Enum

from pydantic import BaseModel, Field

from vibe_ide.models.ticket import TicketStatus


class AgentCreatedInfo(BaseModel):
    role: str
    description: str | None = None


class CreateAgentConversationResponse(BaseModel):
    agent: AgentCreatedInfo | None = None
    message: str = ""
    created: bool = False


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
    doc_updater_enabled: bool = False
    testeur_enabled: bool = False
    test_command: str | None = None
    securite_enabled: bool = False
    validateur_enabled: bool = False


class AgentResult(BaseModel):
    role: str
    ticket_id: str
    content: str
    suggested_status: TicketStatus
    created_tickets: list[str] = Field(default_factory=list)
    duration_ms: int
    # Coût réel de l'appel, pour que l'orchestrateur puisse agréger la dépense
    # d'un run entier (issue #61). Il n'existait auparavant que dans la branche
    # qui écrit en base, donc seulement quand un `run_id` était fourni.
    cost_usd: float = 0.0


class AgentRunRequest(BaseModel):
    project_id: str
    ticket_id: str = ""
    role: str
