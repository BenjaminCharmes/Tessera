---
id: ticket-032
title: "Intégration GitHub Pull Requests"
type: feat
status: done
priority: low
agent: codeur
depends_on:
  - ticket-031
estimated_days: 2
created: 2026-06-21
---

# ticket-032 — Intégration GitHub Pull Requests

## Objectif

Fermer la boucle entre le pipeline vibe-ide et GitHub : quand un ticket est approuvé, l'utilisateur peut ouvrir une PR en un clic. Le statut CI de la PR est affiché en temps réel dans le ticket board.

## Contexte

Avec ticket-031 (sync Issues ↔ tickets), les tickets ont un `github_remote` et potentiellement une issue liée. L'étape naturelle est d'intégrer les PRs : quand le reviewer approuve, proposer d'ouvrir une PR avec titre et description pré-remplis depuis le ticket. Le statut CI (passing/failing) est ensuite visible directement dans `TicketCard`.

## Solution proposée

### `GitHubService` — nouvelles méthodes

```python
async def create_pull_request(
    self,
    title: str,
    body: str,
    head: str,
    base: str = "main",
) -> int:  # numéro de la PR

async def get_pull_request_status(self, pr_number: int) -> PRStatus:
    # Retourne : open/closed/merged + CI checks (passing/failing/pending)

@dataclass
class PRStatus:
    state: Literal["open", "closed", "merged"]
    ci_status: Literal["pending", "passing", "failing", "none"]
    pr_url: str
```

### Endpoint

`POST /api/v1/projects/{project_id}/tickets/{ticket_id}/create-pr`

```json
// Request
{ "head_branch": "ticket-042-oauth-google", "base": "main" }

// Response
{ "pr_number": 15, "pr_url": "https://github.com/..." }
```

### `TicketService` enrichi

Ajouter `pr_number: int | None` dans le frontmatter YAML des tickets.

Étendre `SyncMapService` :
```json
{ "ticket-042": { "issue": 7, "pr": 15 } }
```

### Frontend `TicketCard`

Si `pr_number` défini :
- Badge `⏳ CI en cours` / `✅ CI verte` / `❌ CI rouge` / `🔀 Mergée`
- Polling toutes les 30s via `GET /tickets/{id}/pr-status`

Bouton "Ouvrir une PR" visible si ticket `done` ET projet a `github_remote`.

## Critères d'acceptation

- [ ] Un ticket approuvé (`done`) avec un `github_remote` affiche un bouton "Ouvrir une PR"
- [ ] La PR créée est pré-remplie avec le titre et la description du ticket
- [ ] Le statut CI de la PR (passing/failing/pending) est visible dans `TicketCard`
- [ ] Le `pr_number` est persisté dans le frontmatter du ticket

## Spécifications techniques

**Polling :** `GET /api/v1/projects/{id}/tickets/{ticket_id}/pr-status` toutes les 30s. Arrêt du polling si `state: merged` ou `state: closed`.

Le body de la PR est généré depuis le contenu du ticket Markdown (sections Objectif + Critères d'acceptation).

## Dépendances

- **ticket-031** — `SyncMapService` pour stocker `{ issue, pr }`. Projets avec `github_remote`.

## Estimation

**2j** — Nouvelles méthodes GitHub API + endpoint + frontend polling + tests.

## Risques

- **Moyen** — Le polling 30s peut saturer le rate limit GitHub sur les comptes non-authentifiés. Désactiver le polling si pas de token.
