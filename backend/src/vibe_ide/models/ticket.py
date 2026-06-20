from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field


class TicketStatus(str, Enum):
    todo = "todo"
    in_progress = "in-progress"
    done = "done"
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
    body: str = Field(default="", description="Corps Markdown du ticket")
