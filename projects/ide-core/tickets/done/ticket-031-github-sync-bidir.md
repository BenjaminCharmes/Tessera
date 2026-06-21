---
id: ticket-031
title: "Synchronisation bidirectionnelle tickets ↔ GitHub Issues"
type: feat
status: done
priority: low
agent: codeur
depends_on:
  - ticket-030
estimated_days: 2
created: 2026-06-21
---

# ticket-031 — Sync bidirectionnelle tickets ↔ Issues

## Objectif

Maintenir la cohérence entre les tickets Markdown de vibe-ide et les GitHub Issues : les issues créées sur GitHub apparaissent comme tickets, et les tickets traités dans vibe-ide ferment leurs issues correspondantes. Idempotent et sans collision.

## Contexte

`GithubSyncAgent` existant fait uniquement `issues → tickets` et génère des IDs qui peuvent collisionner avec des tickets locaux existants (ex. issue n°7 → `ticket-007` déjà pris). Ce ticket refactore l'agent pour supporter les deux sens avec un mapping persistant.

Feature **optionnelle par projet** : activée via `agents.json` du projet.

## Solution proposée

### `memory/github-sync-map.json` (par projet)

```json
{ "ticket-042": 7, "ticket-043": 12 }
```

### `backend/src/vibe_ide/services/sync_map.py`

```python
class SyncMapService:
    def load(self, project_path: Path) -> dict[str, int]: ...
    def save(self, project_path: Path, mapping: dict[str, int]) -> None: ...
    def ticket_for_issue(self, issue_number: int) -> str | None: ...
    def issue_for_ticket(self, ticket_id: str) -> int | None: ...
```

### `GitHubService` — nouvelles méthodes

```python
async def create_issue(self, title: str, body: str, labels: list[str]) -> int:
    """Crée une issue, retourne son numéro."""

async def update_issue(self, number: int, title: str, body: str) -> None:
    """Met à jour titre/body."""

async def close_issue(self, number: int) -> None:
    """Ferme une issue (state: closed)."""
```

### `GithubSyncAgent` — refactor

- Mode `pull` : issues ouvertes → tickets (IDs assignés séquentiellement, sans collision)
- Mode `push` : tickets `done` sans issue → créer issue fermée
- Mode `both` : pull puis push
- Log chaque opération dans `memory/github-sync-log.md`

### Endpoint

`POST /api/v1/projects/{project_id}/github/sync`

```json
// Request
{ "direction": "pull" | "push" | "both" }

// Response
{ "pulled": 3, "pushed": 1, "skipped": 2 }
```

### Activation par projet (`agents.json`)

```json
{
  "github_sync": {
    "enabled": true,
    "direction": "both",
    "label_map": { "feat": "enhancement", "fix": "bug" }
  }
}
```

## Critères d'acceptation

- [ ] Une issue GitHub ouverte apparaît comme ticket dans vibe-ide après `pull`
- [ ] Un ticket `done` dans vibe-ide ferme l'issue correspondante après `push`
- [ ] Deux syncs successives ne créent pas de doublons (idempotence)
- [ ] La collision d'IDs (issue n°7 avec ticket-007 existant) est résolue automatiquement
- [ ] Le sync log dans `memory/github-sync-log.md` trace chaque opération

## Spécifications techniques

**Idempotence critique :**
- Vérifier `SyncMapService` avant toute création
- Un ticket déjà mappé → mise à jour, pas nouvelle création
- Utiliser `UPSERT` logique (check existence puis update/create)

Résolution des IDs sans collision :
```python
next_id = max(existing_local_ids) + 1  # jamais utiliser issue_number directement
```

## Dépendances

- **ticket-030** — Les projets avec `github_remote` sont éligibles à la sync.

## Estimation

**2j** — Refactor agent + nouvelles méthodes GitHub API + service mapping + tests idempotence.

## Risques

- **Élevé** — Idempotence difficile à garantir sans le mapping. Tests exhaustifs sur les cas de re-sync.
- **Moyen** — Rate limiting GitHub API (60 req/h sans token, 5000 avec). Prévoir une gestion des 429.
