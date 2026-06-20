---
id: ticket-005
title: Orchestrateur — routing et pipeline codeur→reviewer
type: feat
status: done
priority: high
agent: architect
depends_on: [ticket-003]
created: 2025-06
---

# ticket-005 — Orchestrateur multi-agents

## Contexte

Pour l'instant chaque agent tourne de façon indépendante.
L'orchestrateur coordonne le pipeline complet :
`ticket assigné → codeur → reviewer → done (ou retour au codeur)`

## Tâche

### `Orchestrator` (`services/orchestrator.py`)

```python
class Orchestrator:

    async def run_pipeline(
        self,
        project_id: str,
        ticket_id: str,
        on_event: Callable[[OrchestratorEvent], Awaitable[None]]
    ) -> PipelineResult:
        """
        Pipeline complet pour un ticket de type feat/fix :
        1. Charge le projet et le ticket
        2. Lance le Codeur → attend le résultat
        3. Lance le Reviewer avec le code produit
        4. Si reviewer approve → passe le ticket en DONE
        5. Si reviewer demande des changements → retour au Codeur (max 3 tours)
        6. Émet des events à chaque étape pour le streaming UI
        """

    async def pick_next_ticket(self, project_id: str) -> Optional[Ticket]:
        """
        Sélectionne le prochain ticket à traiter :
        - Status TODO
        - Priorité la plus haute
        - Dépendances toutes DONE
        """

    async def run_autonomous(self, project_id: str, max_tickets: int = 5):
        """
        Mode autonome : traite les tickets les uns après les autres
        jusqu'à épuisement ou max_tickets
        """
```

### `OrchestratorEvent` (pour le streaming)

```python
class EventType(str, Enum):
    AGENT_STARTED = "agent_started"
    AGENT_TOKEN = "agent_token"       # token streamé
    AGENT_DONE = "agent_done"
    TICKET_STATUS_CHANGED = "ticket_status_changed"
    PIPELINE_DONE = "pipeline_done"
    ERROR = "error"

class OrchestratorEvent(BaseModel):
    type: EventType
    agent: Optional[AgentRole] = None
    ticket_id: str
    data: dict
    timestamp: datetime
```

### Endpoint

```
POST /api/v1/orchestrator/run
Body: { project_id, ticket_id }
→ Lance le pipeline, retourne PipelineResult

POST /api/v1/orchestrator/run-autonomous
Body: { project_id, max_tickets: 5 }
→ Lance le mode autonome

WS /api/v1/orchestrator/stream/{project_id}
→ Reçoit les OrchestratorEvents en temps réel
```

### Règles du pipeline

- Max **3 aller-retours** codeur↔reviewer avant d'escalader (passer en BLOCKED)
- Le reviewer doit répondre avec un format structuré : `APPROVED` ou `CHANGES_REQUESTED: {raison}`
- Chaque tour de codeur voit l'historique des feedbacks reviewer précédents
- Logguer chaque transition dans `projects/{id}/memory/pipeline-log.md`

## Critères d'acceptation

- [ ] Pipeline codeur→reviewer fonctionne sur ticket-000 (méta !)
- [ ] Les events WebSocket sont émis à chaque étape
- [ ] Le mode autonome s'arrête proprement à max_tickets
- [ ] Un ticket BLOCKED si 3 tours sans approbation
- [ ] `pick_next_ticket` respecte les dépendances

## Notes

- C'est le ticket le plus complexe — prendre le temps de bien le concevoir
- L'orchestrateur ne doit PAS appeler directement l'API Anthropic — il délègue à `AgentRunner`
- Penser à la concurrence : deux pipelines peuvent tourner en parallèle sur des tickets différents
