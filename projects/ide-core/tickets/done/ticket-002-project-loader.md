---
id: ticket-002
title: Project loader — charger un projet depuis son dossier
type: feat
status: done
priority: critical
agent: codeur
depends_on: [ticket-001]
created: 2025-06
---

# ticket-002 — Project loader

## Contexte

L'orchestrateur doit pouvoir "ouvrir" un projet : lire son `CLAUDE.md`,
découvrir ses agents configurés, et exposer tout ça via l'API.

## Tâche

### `ProjectLoader` (`services/project_loader.py`)

```python
class ProjectLoader:
    def __init__(self, workspace_dir: str):
        self.workspace_dir = workspace_dir  # ex: ~/vibe-ide/projects/

    async def list_projects(self) -> list[Project]:
        # Parcourt workspace_dir/
        # Pour chaque sous-dossier, vérifie l'existence de CLAUDE.md
        # Retourne la liste des projets valides

    async def load_project(self, project_id: str) -> Project:
        # Lit CLAUDE.md
        # Parse les sections "Agents actifs" et "Stack"
        # Retourne un Project hydraté

    async def create_project(
        self,
        project_id: str,
        name: str,
        active_agents: list[str],
        claude_md_content: str
    ) -> Project:
        # Crée la structure de dossiers
        # Écrit le CLAUDE.md
        # Initialise les dossiers tickets/todo, memory/, workspace/
```

### Parsing du CLAUDE.md

Le parsing est intentionnellement simple — pas de format strict imposé.
Extraire :
- `active_agents` : chercher une section "## Agents actifs" et parser les items `-`
- `name` : première ligne `# Titre`
- `stack` : section "## Stack" raw text

### Router `projects.py`

```
GET  /api/v1/projects                → list_projects()
GET  /api/v1/projects/{id}           → load_project(id)
POST /api/v1/projects                → create_project(...)
GET  /api/v1/projects/{id}/context   → retourne le CLAUDE.md complet (pour les agents)
```

### Endpoint `/context` — important

Cet endpoint est ce que les agents appellent au début de chaque session.
Il retourne :

```json
{
  "project_id": "ide-core",
  "claude_md": "# CLAUDE.md complet...",
  "active_agents": ["orchestrateur", "codeur", "reviewer"],
  "open_tickets": [...],
  "recent_decisions": "contenu de memory/decisions.md"
}
```

## Critères d'acceptation

- [ ] `GET /api/v1/projects` liste `ide-core` (et les autres projets présents)
- [ ] `GET /api/v1/projects/ide-core/context` retourne le contexte complet
- [ ] `POST /api/v1/projects` crée un nouveau projet avec la structure correcte
- [ ] Tests pour `ProjectLoader` avec un dossier temporaire

## Notes

- Ne pas essayer de parser le CLAUDE.md avec un LLM ici — parsing simple en Python
- Le parsing "imparfait" est OK : si une section manque, retourner des valeurs par défaut
- Penser à gérer le cas où `memory/decisions.md` n'existe pas encore
