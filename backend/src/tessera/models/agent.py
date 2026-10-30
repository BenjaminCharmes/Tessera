from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

from tessera.models.ticket import TicketStatus


EffortLevel = Literal["low", "medium", "high", "xhigh", "max"]


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


class ServiceDeclare(BaseModel):
    """Un service déclaré dans `services[]` d'un `agents.json` (ADR-042)."""

    nom: str
    commande: str
    cwd: str | None = None
    #: Le fichier d'activité que ce service écrit, relatif à la racine du
    #: projet (ADR-064). Une déclaration humaine : Tessera ne l'écrit jamais.
    activite: str | None = None


class AgentConfig(BaseModel):
    """Un agent tel que décrit dans agents.json d'un projet."""

    role: str
    model: str
    max_tokens: int
    prompt_file: str
    active: bool = True
    max_instances: int = 1
    #: Le rôle lit le web — `WebFetch`, `WebSearch` — et perd `Bash` en
    #: échange (ticket-245). Faux par défaut.
    web: bool = False
    # Le provider se déclare par rôle (ticket-188). Absent : le défaut du
    # backend, comme avant — un manifeste muet ne change pas de comportement.
    provider: str = "agent_sdk"
    fallback: FallbackConfig | None = None
    #: Au-delà de cette taille de prompt (système + utilisateur, en caractères),
    #: un rôle sur `ollama` part d'emblée sur son repli (ticket-714). Absent :
    #: rien ne change. Ignorée sans repli et pour un autre provider qu'`ollama`.
    fallback_above_chars: int | None = Field(default=None, gt=0)
    #: Le point d'accès d'un rôle `openai_compatible` : l'URL de base, sans
    #: `/chat/completions`. Obligatoire pour ce provider, ignorée des autres.
    base_url: str | None = None
    #: Le NOM de la variable d'environnement qui porte la clé de ce point
    #: d'accès, jamais la clé elle-même : `agents.json` se versionne.
    api_key_env: str | None = None
    #: Les skills que ce rôle peut charger (ticket-242). Vide : pas d'outil
    #: `Skill`. La liste borne aussi ce que le CLI découvrirait seul — les
    #: skills de la racine du dépôt et ceux qu'il intègre.
    skills: list[str] = Field(default_factory=list)
    #: L'effort de raisonnement du modèle (ticket-573), parmi les cinq valeurs
    #: du SDK. Absent : rien n'est passé au SDK, qui garde son défaut.
    effort: EffortLevel | None = None


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
    #: Le dossier d'où la commande se lance, relatif au projet, et le temps
    #: qu'elle a pour finir (ticket-241). Absents : le projet, 120 s.
    test_cwd: str | None = None
    test_timeout_s: int | None = None
    securite_enabled: bool = False
    validateur_enabled: bool = False
    #: Le lot de documentation tient aussi le CLAUDE.md du projet, dans un
    #: budget de taille (ticket-244). Faux par défaut : la consigne se déclare.
    doc_claude_md: bool = False


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
    # Les outils que le CLI a refusés pendant l'appel (ticket-515), pour que
    # l'étape les écrive au journal.
    outils_refuses: list[str] = Field(default_factory=list)
    # La sortie validée par le schéma posé à l'appel (ADR-061) ; None sans
    # schéma, ou quand le provider n'a rendu aucune sortie valide.
    structured: dict[str, Any] | None = None


class AgentRunRequest(BaseModel):
    project_id: str
    ticket_id: str = ""
    role: str
