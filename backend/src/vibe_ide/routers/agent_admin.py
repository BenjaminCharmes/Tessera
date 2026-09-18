import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from vibe_ide.config import settings
from vibe_ide.services.agent_registry import AgentNotFoundError, AgentRegistryService

_ROLE_RE = re.compile(r"^[a-z][a-z0-9-]*$")

router = APIRouter(prefix="/agents/registry", tags=["agent-registry"])


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class AgentInfo(BaseModel):
    role: str
    description: str | None = None
    is_builtin: bool
    prompt_preview: str
    #: Quand cet agent parle : `pipeline`, `demande`, ou `jamais` (ticket-097).
    moment: str = "jamais"


class AgentDetailResponse(BaseModel):
    role: str
    is_builtin: bool
    system_prompt: str
    moment: str = "jamais"


class CreateAgentRequest(BaseModel):
    role: str
    system_prompt: str

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if not _ROLE_RE.match(v):
            raise ValueError(
                f"Nom d'agent invalide : '{v}' (doit correspondre à ^[a-z][a-z0-9-]*$)"
            )
        return v

    @field_validator("system_prompt")
    @classmethod
    def validate_system_prompt(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Le system prompt ne peut pas être vide")
        return v


class AgentRegistryResponse(BaseModel):
    agents: list[AgentInfo]


# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------


def get_registry() -> AgentRegistryService:
    # Le dossier des projets sert à savoir quels prompts un `agents.json`
    # branche sur une étape du pipeline (ticket-097).
    return AgentRegistryService(
        settings.ide_prompts_dir, projects_dir=settings.ide_workspace_dir
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=AgentRegistryResponse)
async def list_agents(
    registry: AgentRegistryService = Depends(get_registry),
) -> AgentRegistryResponse:
    infos = registry.list_agents()
    agents: list[AgentInfo] = []
    for info in infos:
        if info.has_prompt:
            try:
                preview = registry.get_prompt(info.role)[:200]
            except AgentNotFoundError:
                preview = ""
        else:
            preview = ""
        agents.append(
            AgentInfo(
                role=info.role,
                description=None,
                is_builtin=info.is_builtin,
                prompt_preview=preview,
                moment=info.moment.value,
            )
        )
    return AgentRegistryResponse(agents=agents)


@router.get("/{role}", response_model=AgentDetailResponse)
async def get_agent(
    role: str,
    registry: AgentRegistryService = Depends(get_registry),
) -> AgentDetailResponse:
    if not _ROLE_RE.match(role):
        raise HTTPException(status_code=422, detail=f"Nom d'agent invalide : '{role}'")
    try:
        prompt = registry.get_prompt(role)
    except AgentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    moment = next(
        (a.moment.value for a in registry.list_agents() if a.role == role), "jamais"
    )
    return AgentDetailResponse(
        role=role,
        is_builtin=registry.is_builtin(role),
        system_prompt=prompt,
        moment=moment,
    )


class UpdateAgentRequest(BaseModel):
    system_prompt: str


@router.put("/{role}", response_model=AgentDetailResponse)
async def update_agent(
    role: str,
    body: UpdateAgentRequest,
    registry: AgentRegistryService = Depends(get_registry),
) -> AgentDetailResponse:
    """Réécrit le prompt d'un agent, natif compris (ticket-079)."""
    if not _ROLE_RE.match(role):
        raise HTTPException(status_code=422, detail=f"Nom d'agent invalide : '{role}'")
    try:
        registry.update_prompt(role, body.system_prompt)
    except AgentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return AgentDetailResponse(
        role=role,
        is_builtin=registry.is_builtin(role),
        system_prompt=body.system_prompt,
    )


@router.post("", response_model=AgentInfo, status_code=201)
async def create_agent(
    body: CreateAgentRequest,
    registry: AgentRegistryService = Depends(get_registry),
) -> AgentInfo:
    try:
        registry.create_agent(body.role, body.system_prompt)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return AgentInfo(
        role=body.role,
        description=None,
        is_builtin=registry.is_builtin(body.role),
        prompt_preview=body.system_prompt[:200],
    )


@router.delete("/{role}", status_code=204)
async def delete_agent(
    role: str,
    registry: AgentRegistryService = Depends(get_registry),
) -> None:
    if not _ROLE_RE.match(role):
        raise HTTPException(status_code=422, detail=f"Nom d'agent invalide : '{role}'")
    try:
        registry.delete_agent(role)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except AgentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
