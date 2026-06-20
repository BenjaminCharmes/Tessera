---
id: ticket-003
title: Agent loop de base — appel Claude avec contexte projet
type: feat
status: todo
priority: critical
agent: codeur
depends_on: [ticket-002]
created: 2025-06
---

# ticket-003 — Agent loop de base

## Contexte

Le cœur du système : comment un agent reçoit un ticket, appelle Claude,
et produit un résultat. Tout le reste s'appuie sur ça.

## Tâche

### `AgentRunner` (`services/agent_runner.py`)

```python
from anthropic import AsyncAnthropic
from ..models.ticket import Ticket
from ..models.agent import AgentRole

class AgentRunner:
    def __init__(self, client: AsyncAnthropic, config: Settings):
        self.client = client
        self.config = config

    async def run(
        self,
        role: AgentRole,
        ticket: Ticket,
        project_context: str,
        stream_callback: Callable[[str], Awaitable[None]] | None = None
    ) -> AgentResult: ...
```

### Modèle `AgentRole` (`models/agent.py`)

```python
class AgentRole(str, Enum):
    ORCHESTRATEUR = "orchestrateur"
    CODEUR = "codeur"
    REVIEWER = "reviewer"
    REDACTEUR = "redacteur"
    ARCHITECT = "architect"
    PROJECT_CREATOR = "project-creator"

class AgentResult(BaseModel):
    role: AgentRole
    ticket_id: str
    content: str           # réponse complète de l'agent
    suggested_status: TicketStatus  # ce que l'agent recommande
    created_tickets: list[str] = []  # ids de tickets créés par cet agent
    duration_ms: int
```

### Construction du prompt

Pour chaque agent, le prompt système est chargé depuis `agents/prompts/{role}.md`.
Voir les prompts détaillés dans `agents/prompts/`.

Le prompt utilisateur est construit ainsi :

```
## Contexte projet
{project_context}   ← contenu de /api/v1/projects/{id}/context

## Ticket assigné
{ticket.body}

## Ta mission
{instruction selon le role}
```

### WebSocket streaming (`routers/agents.py`)

```
POST /api/v1/agents/run
Body: { project_id, ticket_id, role }
→ Lance l'agent, retourne AgentResult

WS /api/v1/agents/stream
→ Même chose mais stream les tokens au fur et à mesure
```

### Gestion des tokens et coûts

Logguer systématiquement :
```python
logger.info("agent_call", extra={
    "role": role,
    "ticket_id": ticket.id,
    "input_tokens": usage.input_tokens,
    "output_tokens": usage.output_tokens,
    "duration_ms": duration_ms,
})
```

## Critères d'acceptation

- [ ] `POST /api/v1/agents/run` avec role=codeur et un ticket-id valide produit une réponse
- [ ] Le streaming WebSocket fonctionne (tester avec wscat ou un test async)
- [ ] Les tokens sont loggués
- [ ] `AgentResult.suggested_status` est toujours un `TicketStatus` valide
- [ ] Test d'intégration avec `ANTHROPIC_API_KEY` réelle (marqué `@pytest.mark.integration`)

## Notes

- Utiliser `claude-sonnet-4-5` comme modèle par défaut
- `max_tokens=8192` pour laisser de la place aux réponses de code
- Activer le prompt caching sur le system prompt (il change peu)
- Ne pas mettre de logique métier dans les routers — tout dans `AgentRunner`
