from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field


class TicketStatus(str, Enum):
    todo = "todo"
    in_progress = "in-progress"
    in_review = "in-review"
    done = "done"
    blocked = "blocked"
    cancelled = "cancelled"


class TicketType(str, Enum):
    # Aligné sur les types Conventional Commits imposés par CLAUDE.md : le type
    # du ticket est repris tel quel comme préfixe du message de commit produit
    # par le pipeline. `design` est un type propre à vibe-ide (tickets confiés à
    # l'agent architect).
    feat = "feat"
    fix = "fix"
    chore = "chore"
    docs = "docs"
    refactor = "refactor"
    test = "test"
    design = "design"


class TicketPriority(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class Ticket(BaseModel):
    id: Annotated[str, Field(description="Identifiant unique, ex: ticket-000")]
    title: str
    type: TicketType
    status: TicketStatus
    priority: TicketPriority
    agent: str
    depends_on: list[str] = Field(default_factory=list)
    created: str = ""
    github_issue_url: str | None = Field(default=None)
    pr_number: int | None = Field(default=None)
    body: str = Field(default="")
    project_id: str = ""
    file_path: str = Field(default="", description="Chemin absolu du fichier sur disque")


class TicketStatusUpdate(BaseModel):
    status: TicketStatus


class TicketCreate(BaseModel):
    """Payload minimal pour créer un ticket depuis l'UI."""

    title: str
    type: TicketType = TicketType.feat
    priority: TicketPriority = TicketPriority.medium
    agent: str = "codeur"
    description: str = ""
    depends_on: list[str] = Field(default_factory=list)


class TicketDraft(BaseModel):
    """Suggestion de ticket générée par le Project Creator — pas encore persisté."""

    title: str
    type: TicketType
    priority: TicketPriority
    agent: str
    description: str


class TicketDraftPlan(BaseModel):
    """Draft généré par le planificateur — pas encore persisté."""

    title: str
    type: str
    priority: str
    agent: str
    description: str
    acceptance_criteria: list[str] = Field(default_factory=list)
    depends_on_index: list[int] = Field(default_factory=list)


class TicketBatchCreate(BaseModel):
    """Payload pour créer plusieurs tickets en une requête."""

    tickets: list[TicketDraftPlan]


class TicketBatchResponse(BaseModel):
    """Réponse après création batch."""

    created: list[Ticket]
