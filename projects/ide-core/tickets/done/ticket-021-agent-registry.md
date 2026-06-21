---
id: ticket-021
title: "Registre d'agents dynamiques (backend, fondation)"
type: refactor
status: done
priority: high
agent: codeur
depends_on: []
created: 2026-06-21
---

# ticket-021 — Registre d'agents dynamiques

## Contexte

Aujourd'hui les agents sont définis par un enum fermé `AgentRole` dans
`backend/src/vibe_ide/models/agent.py`. Si `project-creator` suggère un agent
absent de l'enum (ex. `redacteur`), le pipeline plante à la validation Pydantic.

Ce ticket crée l'infrastructure qui permet des agents dynamiques définis par
un fichier `.md` dans `agents/prompts/`, sans casser les 6 agents built-in.

## Changements

### 1. `backend/src/vibe_ide/services/agent_registry.py` (nouveau)

```python
class AgentRegistryService:
    BUILTIN_ROLES = {"codeur", "reviewer", "orchestrateur", "architect",
                     "project-creator", "project-analyzer"}

    def __init__(self, prompts_dir: Path) -> None: ...

    def list_agents(self) -> list[AgentInfo]:
        """Retourne tous les agents (built-in + custom)."""

    def get_prompt(self, role: str) -> str:
        """Lit le fichier {role}.md. Lève AgentNotFoundError si absent."""

    def create_agent(self, role: str, prompt: str) -> None:
        """Écrit {role}.md. Valide le nom (^[a-z][a-z0-9-]*$)."""

    def delete_agent(self, role: str) -> None:
        """Supprime {role}.md. Refuse les built-in."""

    def is_builtin(self, role: str) -> bool: ...
```

### 2. `backend/src/vibe_ide/models/agent.py`

- `AgentRole` reste un enum pour les 6 built-in (rétrocompatibilité)
- `AgentResult.role` et `AgentRunRequest.role` passent de `AgentRole` à `str`
- Valider via `AgentRegistryService.get_prompt()` au moment de l'exécution,
  pas au niveau Pydantic

### 3. `backend/src/vibe_ide/services/agent_runner.py`

- Remplacer `_load_system_prompt(role: AgentRole)` par une résolution via
  `AgentRegistryService.get_prompt(role)`
- Injecter `AgentRegistryService` dans `AgentRunner.__init__`

### 4. `backend/src/vibe_ide/utils/json_extract.py` (nouveau)

Extraire `_extract_json()` depuis `project_creator.py` dans un utilitaire partagé
pour réutilisation par les tickets 023, 028.

## Critères de done

- [ ] `AgentRegistryService` avec tests unitaires (CRUD, refus built-in, anti-traversal)
- [ ] `AgentResult.role` accepte n'importe quel `str` sans planter Pydantic
- [ ] `AgentRunner` résout le prompt via le registre
- [ ] `_extract_json` dans `utils/json_extract.py`, importé depuis `project_creator.py`
- [ ] Tests existants (`test_orchestrator.py`, `test_github_service.py`) toujours verts
- [ ] `uv run pytest` passe

## Risque

**Medium** — toucher à `AgentRole` impacte orchestrator + routers. Couvrir de
tests de non-régression avant le refactor.
