"""Event and result models exchanged between the orchestrator and its callers.

Split out of `orchestrator.py` so the wire contract of a pipeline run can be
read (and imported) without loading the pipeline engine itself.
"""
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from vibe_ide.models.agent import AgentRole
from vibe_ide.models.ticket import TicketStatus


class EventType(str, Enum):
    AGENT_STARTED = "agent_started"
    AGENT_TOKEN = "agent_token"
    AGENT_TOOL_USE = "agent_tool_use"
    BRANCH_CREATED = "branch_created"
    AGENT_DONE = "agent_done"
    AGENT_QUESTION = "agent_question"
    TICKET_STATUS_CHANGED = "ticket_status_changed"
    PIPELINE_DONE = "pipeline_done"
    ERROR = "error"
    TEST_RESULT = "test_result"
    SECURITY_AUDIT_STARTED = "security_audit_started"
    SECURITY_AUDIT_DONE = "security_audit_done"
    VALIDATION_DONE = "validation_done"
    DOC_UPDATED = "doc_updated"
    COMMIT_CREATED = "commit_created"
    QUOTA_UPDATED = "quota_updated"
    QUEUE_PROGRESS = "queue_progress"


class OrchestratorEvent(BaseModel):
    type: EventType
    agent: Optional[AgentRole] = None
    ticket_id: str
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PipelineResult(BaseModel):
    ticket_id: str
    final_status: TicketStatus
    rounds: int
    approved: bool
    branch: str | None = None
    commit_sha: str | None = None


EventCallback = Callable[[OrchestratorEvent], Awaitable[None]]
