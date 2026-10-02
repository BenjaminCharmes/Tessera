"""Event and result models exchanged between the orchestrator and its callers.

Split out of `orchestrator.py` so the wire contract of a pipeline run can be
read (and imported) without loading the pipeline engine itself.
"""
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from tessera.models.agent import AgentRole
from tessera.models.ticket import TicketStatus
from tessera.services.livraison import Livraison


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
    #: Un provider n'a pas répondu et son repli a servi (ticket-188). Sans
    #: cet événement, rien à l'écran ne distingue un audit sur le modèle
    #: prévu d'un audit sur son remplaçant.
    PROVIDER_FALLBACK = "provider_fallback"
    QUEUE_PROGRESS = "queue_progress"
    #: Ce que la livraison a fait du commit du run (ticket-083).
    LIVRAISON_DONE = "livraison_done"
    #: Le run est fini **et** le projet est libre (ticket-128). Distinct de
    #: `pipeline_done`, que l'orchestrateur publie avant de rendre la main :
    #: entre les deux, le projet est encore marqué occupé. Depuis que le POST
    #: ne porte plus le résultat, c'est aussi ici que `arret` devient lisible
    #: (ADR-037).
    RUN_CLOSED = "run_closed"
    #: Une ligne écrite par un service lancé pour un projet (ticket-137).
    #: Jetable comme un token : un serveur bavard ne doit pas noyer les
    #: transitions d'un run dans la file d'un observateur lent.
    SERVICE_OUTPUT = "service_output"
    #: Un service s'est terminé, avec son code de sortie (ticket-145). Sans
    #: lui, l'écran ne pourrait apprendre sa mort qu'en sondant en boucle.
    SERVICE_CLOSED = "service_closed"
    #: La mise à jour de la documentation a échoué (ticket-213). Sans cet
    #: événement, l'échec reste dans les logs du backend, invisible à l'écran.
    DOCUMENTATION_FAILED = "documentation_failed"
    #: La validation des critères d'acceptation démarre (ticket-255). Émis
    #: seulement si le validateur est actif — un run sans validateur ne produit
    #: pas cet événement.
    VALIDATION_STARTED = "validation_started"
    #: La mise à jour de la documentation démarre (ticket-255). Émis seulement
    #: sur un run approuvé disposant d'un documenteur.
    DOCUMENTATION_STARTED = "documentation_started"
    #: La livraison du commit démarre (ticket-255). Émis seulement sur un run
    #: approuvé dont le projet autorise au moins `pr`.
    LIVRAISON_STARTED = "livraison_started"
    #: La phase 2 de la livraison est terminée — CI attendue et merge tenté
    #: (ticket-306). Émis par `CIWatcher` après chaque merge ou échec de CI.
    #: `merged` indique si la PR a été mergée ; `arret` contient la raison du
    #: blocage quand `merged` est faux.
    CI_MERGE_DONE = "ci_merge_done"


class OrchestratorEvent(BaseModel):
    type: EventType
    agent: Optional[AgentRole] = None
    ticket_id: str
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    #: De quel run vient l'événement, et sur quel projet (ticket-128). Le
    #: canal d'observation porte tous les runs à la fois : sans ces deux
    #: champs, un client ne saurait pas à quelle carte rattacher ce qu'il
    #: reçoit. Optionnels, parce que l'orchestrateur les ignore — c'est le
    #: routeur qui les renseigne au moment de publier.
    run_id: Optional[str] = None
    project_id: Optional[str] = None


class PipelineResult(BaseModel):
    ticket_id: str
    final_status: TicketStatus
    rounds: int
    approved: bool
    branch: str | None = None
    commit_sha: str | None = None
    #: Ce que la livraison a fait du commit, et où elle s'est arrêtée
    #: (ticket-083). `None` quand aucune livraison n'a été tentée.
    livraison: Livraison | None = None
    #: La panne qui a interrompu la production, quand il y en a eu une
    #: (ticket-102). Le run rend un résultat non approuvé plutôt qu'une
    #: erreur serveur : sans ce champ, la cause ne serait lisible que dans
    #: les logs du backend, là où l'utilisateur de l'IDE ne va pas.
    arret: str | None = None


EventCallback = Callable[[OrchestratorEvent], Awaitable[None]]
