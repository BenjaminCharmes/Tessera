# Référence API

Table générée depuis `openapi.json` — la source fait foi, et `/docs` la sert
en interactif quand le backend tourne.

### Santé

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/health` | Health |

### Projets

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/api/v1/projects` | List Projects |
| `GET` | `/api/v1/projects/overview` | List Projects Overview |
| `POST` | `/api/v1/projects` | Create Project |
| `POST` | `/api/v1/projects/clone` | Clone Project |
| `POST` | `/api/v1/projects/import` | Import Project |
| `POST` | `/api/v1/projects/from-template` | Create Project From Template |
| `GET` | `/api/v1/projects/usage/breakdown` | Get Usage Breakdown Global |
| `GET` | `/api/v1/projects/{project_id}` | Get Project |
| `GET` | `/api/v1/projects/{project_id}/icon` | Get Project Icon |
| `DELETE` | `/api/v1/projects/{project_id}` | Delete |
| `GET` | `/api/v1/projects/{project_id}/agents` | Get Project Agents |
| `PUT` | `/api/v1/projects/{project_id}/agents/{role}` | Set Project Agent Model |
| `POST` | `/api/v1/projects/{project_id}/analyze` | Analyze Project |
| `GET` | `/api/v1/projects/{project_id}/artifacts` | Get Artifact Mode |
| `PUT` | `/api/v1/projects/{project_id}/artifacts` | Set Artifact Mode |
| `GET` | `/api/v1/projects/{project_id}/branches/cleanup` | Get Cleanup Plan |
| `POST` | `/api/v1/projects/{project_id}/branches/cleanup` | Run Cleanup |
| `GET` | `/api/v1/projects/{project_id}/context` | Get Project Context |
| `POST` | `/api/v1/projects/{project_id}/detach` | Detach |
| `POST` | `/api/v1/projects/{project_id}/git/init` | Init Git |
| `POST` | `/api/v1/projects/{project_id}/git/link` | Link Git Remote |
| `GET` | `/api/v1/projects/{project_id}/git/status` | Get Git Status |
| `POST` | `/api/v1/projects/{project_id}/github/sync` | Github Sync |
| `POST` | `/api/v1/projects/{project_id}/plan` | Plan Project |
| `GET` | `/api/v1/projects/{project_id}/removal-plan` | Get Removal Plan |
| `GET` | `/api/v1/projects/{project_id}/runs` | List Project Runs |
| `GET` | `/api/v1/projects/{project_id}/usage` | Get Usage |
| `GET` | `/api/v1/projects/{project_id}/usage/breakdown` | Get Usage Breakdown For Project |

### Tickets

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/api/v1/projects/{project_id}/tickets` | List Tickets |
| `POST` | `/api/v1/projects/{project_id}/tickets` | Create Ticket |
| `GET` | `/api/v1/projects/{project_id}/tickets/archive` | List Archived Tickets |
| `POST` | `/api/v1/projects/{project_id}/tickets/batch` | Create Tickets Batch |
| `GET` | `/api/v1/projects/{project_id}/pr-statuses` | List PR Statuses For Project |
| `GET` | `/api/v1/projects/{project_id}/tickets/{ticket_id}` | Get Ticket |
| `PATCH` | `/api/v1/projects/{project_id}/tickets/{ticket_id}` | Update Ticket Status |
| `GET` | `/api/v1/projects/{project_id}/tickets/{ticket_id}/activity` | Get Ticket Activity |
| `GET` | `/api/v1/projects/{project_id}/tickets/{ticket_id}/runs` | List Runs For Ticket |
| `POST` | `/api/v1/projects/{project_id}/tickets/{ticket_id}/create-pr` | Create Pull Request |
| `GET` | `/api/v1/projects/{project_id}/tickets/{ticket_id}/diff` | Get Ticket Diff |
| `POST` | `/api/v1/projects/{project_id}/tickets/{ticket_id}/merge-pr` | Merge Pull Request For Ticket |
| `POST` | `/api/v1/projects/{project_id}/tickets/{ticket_id}/open-pr` | Open Pull Request For Ticket |
| `GET` | `/api/v1/projects/{project_id}/tickets/{ticket_id}/pr-status` | Get Pr Status |

### Signalements

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `POST` | `/api/v1/signalements` | Report Tessera Bug or Idea |

L'endpoint accepte un signalement (bug ou idée) sur Tessera. Il crée automatiquement un ticket dans le projet `ide-core`.

**Réponse selon le contexte** :

- **Projet `ide-core` libre** (aucun run en cours) : le signalement est écrit immédiatement dans `tickets/todo/`. Réponse `201 Created`.
- **Un run `ide-core` actif** : le signalement attend dans une file en dehors du dépôt (répertoire `IDE_STATE_DIR`, fichier `signalements_en_attente.json`). Réponse `202 Accepted` avec `{ "en_attente": true, "position": n }`. Une fois le run fusionné, les signalements en attente sont écrits en ordre d'arrivée.

### Chat

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/api/v1/projects/{project_id}/chat` | List Conversations |
| `POST` | `/api/v1/projects/{project_id}/chat/run` | Run Pipeline From Chat |
| `GET` | `/api/v1/projects/{project_id}/chat/{conversation_id}` | Get Chat History |

### Agents

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `POST` | `/api/v1/agents/create-agent` | Create Agent |
| `POST` | `/api/v1/agents/create-project` | Create Project |
| `GET` | `/api/v1/agents/registry` | List Agents |
| `POST` | `/api/v1/agents/registry` | Create Agent |
| `GET` | `/api/v1/agents/registry/{role}` | Get Agent |
| `PUT` | `/api/v1/agents/registry/{role}` | Update Agent |
| `DELETE` | `/api/v1/agents/registry/{role}` | Delete Agent |
| `POST` | `/api/v1/agents/run` | Run Agent |

### Orchestrateur

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `POST` | `/api/v1/orchestrator/run` | Run Pipeline |
| `POST` | `/api/v1/orchestrator/run-autonomous` | Run Autonomous |

#### `POST /api/v1/orchestrator/run`

Lance un run et répond sans l'attendre. Le run s'observe sur
`WS /api/v1/orchestrator/observe`, et se suit par `GET /api/v1/runs/{run_id}`.

| Champ | Type | Défaut | Rôle |
|-------|------|--------|------|
| `project_id` | `string` | — | Projet visé (obligatoire). |
| `mode` | `single` \| `queue` \| `autonomous` | `single` | Un ticket, une file, ou le mode autonome. |
| `ticket_id` | `string` | — | Le ticket à traiter. Obligatoire en `single`. |
| `ticket_ids` | `string[]` | `[]` | Les tickets de la file, dans l'ordre. Lu en `queue`. |
| `max_tickets` | `int` | `5` | Nombre maximal de tickets. Lu en `autonomous`. |
| `depuis_github` | `bool` | `false` | Tire d'abord les issues `agent-ready`. Lu en `autonomous`. |
| `budget_usd` | `float` > 0 | calculé | Plafond de dépense de la file, qui remplace le plafond par ticket × nombre de tickets. Lu en `queue`. |

Exemple, une file de trois tickets :

```json
{
  "project_id": "mon-projet",
  "mode": "queue",
  "ticket_ids": ["ticket-001", "ticket-002", "ticket-003"],
  "budget_usd": 6.0
}
```

Réponse `202` :

```json
{ "run_id": "92571cf0d5f64a4a8b7d3c1e0f2a9b64" }
```

`run_id` est l'identifiant à garder : il sert à `GET /runs/{run_id}` et à
`GET /runs/{run_id}/events`, pendant la file comme après.

Refus : `409` si le projet porte déjà un run, `422` si `ticket_id` manque en
`single` ou si la livraison déclarée ne peut pas aboutir, `404` si le projet
est inconnu.

### Runs

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/api/v1/runs/{run_id}` | Get Status |
| `GET` | `/api/v1/runs/{run_id}/events` | Get Events |

`GET /runs/{run_id}` répond, pour un run vivant comme terminé :

```json
{
  "project_id": "mon-projet",
  "mode": "queue",
  "statut": "en cours",
  "ticket_courant": "ticket-002",
  "faits": ["ticket-001"],
  "restants": ["ticket-003"],
  "debut": "2026-10-14T10:00:00+00:00",
  "fin": null
}
```

- `statut` vaut `en cours`, `terminé` ou `interrompu`. Une file arrêtée sur
  budget, sur limite de session ou sur un ticket non approuvé, ou dont le
  dernier ticket est `blocked`, est `interrompu`.
- Run vivant : `ticket_courant`, `faits` et `restants` suivent la file en
  temps réel. Run terminé : `ticket_courant` est `null`, `faits` liste les
  tickets que la file a joués (un ticket sauté parce qu'il était déjà
  `done` n'y figure pas) et `restants` ceux que la dernière annonce de
  progression laissait en attente.
- `404` si l'identifiant est inconnu. Les files lancées avant ce suivi gardent
  un identifiant de lancement introuvable ; leurs lignes restent lisibles par
  `GET /projects/{project_id}/runs`.

`GET /runs/{run_id}/events` rend les évènements persistés du run, dans l'ordre
d'émission, jetons exclus. Avec l'identifiant d'une file, il rend ceux de toute
la file ; avec celui d'un ticket de la file, ceux de ce ticket seul.

### Services

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/api/v1/services/running` | List Running Services |
| `POST` | `/api/v1/services/running/{pid}/stop` | Stop Service |

### Fichiers

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/api/v1/fs/list` | List Dir |
| `GET` | `/api/v1/fs/read` | Read File |
| `PUT` | `/api/v1/fs/write` | Write File |
