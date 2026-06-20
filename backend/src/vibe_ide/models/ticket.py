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
    feat = "feat"
    fix = "fix"
    chore = "chore"
    design = "design"
    docs = "docs"


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
    body: str = Field(default="")
    project_id: str = ""
    file_path: str = Field(default="", description="Chemin absolu du fichier sur disque")


class TicketStatusUpdate(BaseModel):
    status: TicketStatus


class TicketDraft(BaseModel):
    """Suggestion de ticket générée par le Project Creator — pas encore persisté."""

    title: str
    type: TicketType
    priority: TicketPriority
    agent: str
    description: str
