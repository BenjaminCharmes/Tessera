# Référence API

Le backend sert aussi `/docs` en interactif quand il tourne.

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
| `POST` | `/api/v1/projects` | Create Project |
| `POST` | `/api/v1/projects/clone` | Clone Project |
| `POST` | `/api/v1/projects/import` | Import Project |
| `GET` | `/api/v1/projects/usage/breakdown` | Get Usage Breakdown Global |
| `GET` | `/api/v1/projects/{project_id}` | Get Project |
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
| `GET` | `/api/v1/projects/{project_id}/tickets/{ticket_id}` | Get Ticket |
| `PATCH` | `/api/v1/projects/{project_id}/tickets/{ticket_id}` | Update Ticket Status |
| `GET` | `/api/v1/projects/{project_id}/tickets/{ticket_id}/activity` | Get Ticket Activity |
| `POST` | `/api/v1/projects/{project_id}/tickets/{ticket_id}/create-pr` | Create Pull Request |
| `GET` | `/api/v1/projects/{project_id}/tickets/{ticket_id}/diff` | Get Ticket Diff |
| `POST` | `/api/v1/projects/{project_id}/tickets/{ticket_id}/merge-pr` | Merge Pull Request For Ticket |
| `POST` | `/api/v1/projects/{project_id}/tickets/{ticket_id}/open-pr` | Open Pull Request For Ticket |
| `GET` | `/api/v1/projects/{project_id}/tickets/{ticket_id}/pr-status` | Get Pr Status |

### Chat

| Méthode | Endpoint | Description |
|---------|----------|-------------|
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

### Fichiers

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/api/v1/fs/list` | List Dir |
| `GET` | `/api/v1/fs/read` | Read File |
| `PUT` | `/api/v1/fs/write` | Write File |
