---
id: ticket-001
title: Modèles Pydantic et service de tickets
type: feat
status: todo
priority: critical
agent: codeur
depends_on: [ticket-000]
created: 2025-06
---

# ticket-001 — Modèles Pydantic et service de tickets

## Contexte

Les tickets sont la colonne vertébrale de la communication entre agents.
Un ticket est un fichier Markdown avec un frontmatter YAML.

Exemple de ticket sur disque :
```
---
id: ticket-042
title: Ajouter la validation des emails
type: feat
status: todo
priority: high
agent: codeur
depends_on: [ticket-038]
created: 2025-06-01
---

# Description longue ici...
```

## Tâche

### 1. Modèle `Ticket` (`models/ticket.py`)

```python
from enum import Enum
from typing import Optional
from pydantic import BaseModel

class TicketStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in-progress"
    IN_REVIEW = "in-review"
    DONE = "done"
    BLOCKED = "blocked"

class TicketType(str, Enum):
    FEAT = "feat"
    FIX = "fix"
    CHORE = "chore"
    DESIGN = "design"
    DOCS = "docs"

class TicketPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class Ticket(BaseModel):
    id: str
    title: str
    type: TicketType
    status: TicketStatus
    priority: TicketPriority
    agent: str
    depends_on: list[str] = []
    created: str
    body: str  # contenu Markdown après le frontmatter
    project_id: str
    file_path: str  # chemin absolu sur disque
```

### 2. Modèle `Project` (`models/project.py`)

```python
class Project(BaseModel):
    id: str               # nom du dossier (ex: "ide-core")
    name: str             # titre lisible
    path: str             # chemin absolu
    active_agents: list[str]
    stack: Optional[str] = None
    raw_claude_md: str    # contenu brut du CLAUDE.md
```

### 3. Service `TicketService` (`services/ticket_service.py`)

Méthodes à implémenter :

```python
class TicketService:
    def __init__(self, project_path: str): ...

    async def list_tickets(
        self,
        status: Optional[TicketStatus] = None
    ) -> list[Ticket]: ...
    # Parcourt les dossiers todo/, in-progress/, done/
    # Parse le frontmatter avec python-frontmatter
    # Filtre par status si fourni

    async def get_ticket(self, ticket_id: str) -> Optional[Ticket]: ...

    async def update_status(
        self,
        ticket_id: str,
        new_status: TicketStatus
    ) -> Ticket: ...
    # Déplace le fichier entre les dossiers
    # Met à jour le frontmatter status

    async def create_ticket(self, ticket: Ticket) -> Ticket: ...
    # Crée le fichier Markdown dans todo/
    # Génère l'id si non fourni (ticket-NNN)
```

### 4. Router `tickets.py` (`routers/tickets.py`)

```
GET    /api/v1/projects/{project_id}/tickets          → list
GET    /api/v1/projects/{project_id}/tickets/{id}     → get
PATCH  /api/v1/projects/{project_id}/tickets/{id}     → update status
POST   /api/v1/projects/{project_id}/tickets          → create
```

## Critères d'acceptation

- [ ] `TicketService.list_tickets()` lit correctement les tickets du projet `ide-core`
- [ ] Le déplacement de fichier lors du changement de status fonctionne
- [ ] `GET /api/v1/projects/ide-core/tickets` retourne la liste des tickets
- [ ] Tests unitaires pour `TicketService` (mock filesystem avec `tmp_path` pytest)
- [ ] Pas de `Any` dans les types

## Notes

- Utiliser `python-frontmatter` pour parser le Markdown
- Le `body` du ticket est tout ce qui suit le bloc `---` de fermeture
- L'`id` dans le frontmatter fait foi — pas le nom de fichier
