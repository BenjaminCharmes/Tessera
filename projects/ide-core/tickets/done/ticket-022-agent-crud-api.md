---
id: ticket-022
title: "API CRUD agents dynamiques"
type: feat
status: done
priority: high
agent: codeur
depends_on:
  - ticket-021
estimated_days: 0.5
created: 2026-06-21
---

# ticket-022 — API CRUD agents dynamiques

## Objectif

Exposer le registre d'agents (ticket-021) via une API REST, afin que l'UI et des outils externes puissent lister, consulter, créer et supprimer des agents sans accès direct au filesystem.

## Contexte

Après ticket-021, `AgentRegistryService` existe mais n'est accessible que via le code Python. Pour que le frontend (ticket-024) et d'autres services puissent gérer les agents, il faut une API REST sécurisée. La sécurité est critique : les roles passent dans les chemins de fichiers, toute injection = path traversal.

## Solution proposée

Nouveau router `backend/src/vibe_ide/routers/agent_admin.py` monté sur `/api/v1/agents/registry`.

### Endpoints

| Méthode | Path | Description |
|---|---|---|
| `GET` | `/agents/registry` | Liste tous les agents (built-in + custom) |
| `GET` | `/agents/registry/{role}` | Contenu complet du system prompt |
| `POST` | `/agents/registry` | Créer/mettre à jour un agent custom |
| `DELETE` | `/agents/registry/{role}` | Supprimer un agent (built-in refusé) |

### Modèles Pydantic

```python
class AgentInfo(BaseModel):
    role: str
    description: str | None
    is_builtin: bool
    prompt_preview: str   # 200 premiers caractères

class CreateAgentRequest(BaseModel):
    role: str             # validé : ^[a-z][a-z0-9-]*$
    system_prompt: str    # non vide

class AgentRegistryResponse(BaseModel):
    agents: list[AgentInfo]
```

## Critères d'acceptation

- [ ] `GET /agents/registry` retourne la liste complète avec badge built-in/custom
- [ ] `POST /agents/registry` crée un fichier prompt et retourne `201`
- [ ] `DELETE /agents/registry/{role}` sur un built-in retourne `403` avec message explicite
- [ ] Un `role` malformé (`../secrets`, `foo bar`) retourne `422` avant toute opération filesystem

## Spécifications techniques

**Sécurité critique :**
- Valider `role` avec `^[a-z][a-z0-9-]*$` dès la réception (avant toute I/O)
- Ne jamais concaténer l'input brut dans un chemin (Path traversal)
- `DELETE` sur un built-in → 403, sur un inexistant → 404

**Montage dans `main.py` :**
```python
app.include_router(agent_admin.router, prefix="/api/v1")
```

## Dépendances

- **ticket-021** — Nécessite `AgentRegistryService` pour les opérations CRUD.

## Estimation

**0.5j** — Router CRUD standard, logique dans le service existant.

## Risques

- **Faible** — API isolée, pas d'impact sur le pipeline existant.
