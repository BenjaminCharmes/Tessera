from fastapi import APIRouter

from vibe_ide.models.agent import AgentRunRequest, AgentRunResult

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/run", response_model=AgentRunResult)
async def run_agent(request: AgentRunRequest) -> AgentRunResult:
    return AgentRunResult(
        ticket_id=request.ticket_id,
        role=request.role,
        success=False,
        error="Not implemented yet",
    )
