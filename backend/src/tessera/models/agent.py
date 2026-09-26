from enum import Enum

from pydantic import BaseModel, Field

from tessera.models.ticket import TicketStatus


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


class FallbackConfig(BaseModel):
    """Sur quoi retomber quand le provider d'un rôle ne répond pas (ticket-188)."""

    provider: str
    model: str


class AgentConfig(BaseModel):
    """Un agent tel que décrit dans agents.json d'un projet."""

    role: str
    model: str
    max_tokens: int
    prompt_file: str
    active: bool = True
    max_instances: int = 1
    # Le provider se déclare par rôle (ticket-188). Absent : le défaut du
    # backend, comme avant — un manifeste muet ne change pas de comportement.
    provider: str = "agent_sdk"
    fallback: FallbackConfig | None = None


class AgentPipelineConfig(BaseModel):
    """Section pipeline de agents.json.

    Chaque champ ici est lu quelque part — `test_consignes_coherentes.py` le
    vérifie. `default` et `auto_merge_on_approve` en ont été retirés
    (ticket-091) : rien ne les lisait, et le second était écrit à `true` dans
    chaque projet créé. Dans un produit dont toute la question est de savoir
    qui a le droit de merger, un réglage nommé « merge automatique » qui ne
    fait rien est pire qu'absent — on le lit, et on le croit. Qui merge est
    décidé par `autonomy` (ADR-029).
    """

    max_review_rounds: int = 3
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
    # La conversation du provider, à reprendre au tour suivant (ticket-187).
    # None quand le provider n'en rend pas : le tour suivant repart à froid.
    session_id: str | None = None


class AgentRunRequest(BaseModel):
    project_id: str
    ticket_id: str = ""
    role: str
