"""Agents declared by a project and their model — ticket-080, ticket-188, ticket-689."""

from fastapi import HTTPException
from pydantic import BaseModel

from tessera.config import settings
from tessera.models.agent import FallbackConfig
from tessera.routers.projects.shared import new_router
from tessera.services.cost_calculator import modeles_connus
from tessera.services.project_loader import (
    AgentAbsentDuProjet,
    ModeleInconnu,
    load_agents_config,
    set_agent_model,
    set_agent_provider,
)
from tessera.services.providers.noms import PROVIDERS_ANTHROPIC, PROVIDERS_CONNUS, ProviderInconnu

router = new_router()


class ProjectAgentConfig(BaseModel):
    role: str
    model: str
    max_tokens: int
    active: bool = True
    provider: str = "agent_sdk"
    fallback: FallbackConfig | None = None


class ProjectAgentsResponse(BaseModel):
    agents: list[ProjectAgentConfig]
    #: Les seuls modèles proposables sur un provider Anthropic : ceux dont
    #: l'app sait calculer le coût.
    known_models: list[str]
    #: Les providers qu'un rôle peut déclarer (ticket-188).
    known_providers: list[str]
    #: Par provider, la liste proposable — vide quand le nom est libre.
    known_models_by_provider: dict[str, list[str]]


class SetModelRequest(BaseModel):
    model: str
    provider: str | None = None
    fallback: FallbackConfig | None = None


def _modeles_par_provider() -> dict[str, list[str]]:
    return {
        nom: modeles_connus() if nom in PROVIDERS_ANTHROPIC else []
        for nom in PROVIDERS_CONNUS
    }


@router.get("/{project_id}/agents", response_model=ProjectAgentsResponse)
async def get_project_agents(project_id: str) -> ProjectAgentsResponse:
    """Les agents déclarés par ce projet, et le modèle que chacun utilise."""
    try:
        configs = load_agents_config(settings.ide_workspace_dir / project_id)
    except ProviderInconnu as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ProjectAgentsResponse(
        agents=[
            ProjectAgentConfig(
                role=c.role, model=c.model, max_tokens=c.max_tokens, active=c.active,
                provider=c.provider, fallback=c.fallback,
            )
            for c in configs
        ],
        known_models=modeles_connus(),
        known_providers=list(PROVIDERS_CONNUS),
        known_models_by_provider=_modeles_par_provider(),
    )


@router.put("/{project_id}/agents/{role}", response_model=ProjectAgentsResponse)
async def set_project_agent_model(
    project_id: str, role: str, body: SetModelRequest
) -> ProjectAgentsResponse:
    """Change le modèle d'un agent pour **ce projet** (ticket-080), et depuis
    ticket-188 son provider et son repli. `fallback` omis : le repli ne bouge
    pas ; `fallback: null` : il est retiré."""
    project_path = settings.ide_workspace_dir / project_id
    try:
        if body.provider is not None or "fallback" in body.model_fields_set:
            actuel = next(
                (c for c in load_agents_config(project_path) if c.role == role), None
            )
            if actuel is None:
                raise AgentAbsentDuProjet(f"L'agent '{role}' n'est pas déclaré ici")
            repli = (
                body.fallback.model_dump() if body.fallback is not None else None
            ) if "fallback" in body.model_fields_set else (
                actuel.fallback.model_dump() if actuel.fallback is not None else None
            )
            set_agent_provider(project_path, role, body.provider or actuel.provider, repli)
        set_agent_model(project_path, role, body.model)
    except (ModeleInconnu, ProviderInconnu) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except AgentAbsentDuProjet as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return await get_project_agents(project_id)
