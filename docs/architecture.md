# Architecture — vibe-ide

## Vue d'ensemble

```
┌─────────────────────────────────────────┐
│       ✅ Tauri v2 Shell (Rust)          │   ← ticket-010
│  ┌───────────────────────────────────┐  │
│  │   ✅ React UI (TypeScript)        │  │   ← tickets 007-014
│  │  Monaco Editor (local bundle)     │  │
│  │  Ticket Board · Agent Stream      │  │
│  │  Sidebar (projets + tickets)      │  │
│  │  CreateProjectModal               │  │
│  └──────────────┬────────────────────┘  │
└─────────────────┼───────────────────────┘
                  │ HTTP + WebSocket
┌─────────────────▼───────────────────────┐
│       Orchestrateur (FastAPI Python)    │   ← ✅ implémenté
│                                         │
│  Routers                Services        │
│  ├─ /projects      ├─ ProjectLoader     │
│  ├─ /tickets       ├─ TicketService     │
│  ├─ /agents        ├─ AgentRunner       │
│  └─ /orchestrator  ├─ Orchestrator      │
│                    ├─ ProjectCreator    │
│                    ├─ GitHubService     │
│                    ├─ GithubSyncAgent   │
│                    ├─ GitWorkspaceSvc   │
│                    └─ DatabaseService   │
│                           │             │
│              LLMProvider (ADR-017)      │
│      ┌────────────────┴──────────────┐  │
│  ClaudeAgentSDKProvider     AnthropicApi│
│  (défaut — abonnement,      Provider    │
│   outils fichier)           (fallback)  │
└─────────────────────────────────────────┘
                  │
       Filesystem (tickets Markdown + mémoire)
                  │
       git (une branche + un commit par run — ADR-018)
                  │
       SQLite  vibe_ide.db  (historique pipelines)
```

### Couche LLM (ADR-017)

Les services n'appellent jamais Claude directement : ils passent par le protocole
`LLMProvider` (`complete` / `stream`). Deux implémentations coexistent —
`ClaudeAgentSDKProvider` (défaut, facturé sur l'**abonnement**, dispose des outils
fichier) et `AnthropicApiProvider` (fallback sur crédits API, pour les
environnements sans session interactive : Docker, CI).

`get_provider(allow_tools=False)` retourne une variante **sans outils**, utilisée
par tous les services purement texte→JSON (validateur, auditeur sécurité,
planificateur, project-analyzer, agent-creator, project-creator, doc-updater) qui
écrivent eux-mêmes leurs fichiers en Python.

### Couche git (ADR-018)

`GitWorkspaceService` isole les opérations git du pipeline, et ne s'applique
**jamais** au dépôt de vibe-ide lui-même — uniquement au projet ciblé.

## Endpoints implémentés

### Projets
| Méthode | Route | Description |
|---------|-------|-------------|
| `GET` | `/api/v1/projects` | Liste tous les projets (dossiers avec CLAUDE.md) |
| `POST` | `/api/v1/projects` | Crée la structure filesystem d'un projet |
| `GET` | `/api/v1/projects/{id}` | Charge le projet et son CLAUDE.md |
| `GET` | `/api/v1/projects/{id}/context` | Contexte complet (tickets ouverts + décisions) |
| `GET` | `/api/v1/projects/{id}/runs` | Historique des pipelines (SQLite, limite configurable) |

### Tickets
| Méthode | Route | Description |
|---------|-------|-------------|
| `GET` | `/api/v1/projects/{id}/tickets` | Liste les tickets (optionnel: `?status=todo`) |
| `POST` | `/api/v1/projects/{id}/tickets` | Crée un ticket (génère le fichier Markdown) |
| `GET` | `/api/v1/projects/{id}/tickets/{tid}` | Détail d'un ticket |
| `PATCH` | `/api/v1/projects/{id}/tickets/{tid}/status` | Déplace le ticket dans le bon dossier |

### Agents
| Méthode | Route | Description |
|---------|-------|-------------|
| `POST` | `/api/v1/agents/run` | Exécute un agent sur un ticket (sans streaming) |
| `WS` | `/api/v1/agents/stream` | Exécute un agent avec streaming de tokens |
| `POST` | `/api/v1/agents/create-project` | Crée un projet via conversation multi-tours |

### Orchestrateur
| Méthode | Route | Description |
|---------|-------|-------------|
| `POST` | `/api/v1/orchestrator/run` | Lance le pipeline codeur→reviewer (sauvegarde en DB) |
| `POST` | `/api/v1/orchestrator/run-autonomous` | Mode autonome (N tickets en séquence) |
| `WS` | `/api/v1/orchestrator/stream/{project_id}` | Stream des OrchestratorEvents + sauvegarde en DB |

## Flux d'un ticket

```
 1. Ticket en todo/ → POST /orchestrator/run { project_id, ticket_id }
 2. DB : create_run(project_id, ticket_id) → run_id
 3. Garde-fou : arbre de travail sale ? → ticket → blocked/, run terminé
 4. Orchestrateur: ticket → in-progress/
 5. git checkout -b ticket-XXX-slug  (forkée de la ref de base, pas du ticket
    précédent) → OrchestratorEvent.BRANCH_CREATED
 6. Codeur (Claude) → ÉCRIT RÉELLEMENT les fichiers (outils fichier du SDK)
    └─ tokens streamés via WS → UI en temps réel
    └─ chaque event → save_event(run_id, ...)
 7. git diff → c'est CE diff qui alimente toutes les étapes suivantes
    (repli sur la prose du codeur si le diff est vide)
 8. Testeur → exécute la suite de tests du projet → TEST_RESULT
 9. Auditeur sécurité (OWASP) → BLOCK si CRITICAL/HIGH → ticket → blocked/
10. Ticket → in-review/
11. Reviewer (Claude) → relit le diff
    ├─ "APPROVED" → étape 12
    └─ "CHANGES_REQUESTED: {raison}" → retour au Codeur avec feedback
         (max 3 tours ; sinon ticket → blocked/)
12. Validateur → vérifie les critères d'acceptation un par un
13. Doc-updater → met à jour README / docs / CLAUDE.md du projet
14. git commit — sur TOUS les chemins de sortie :
    ├─ approuvé      → "<type>: ticket-XXX — <titre>" puis advance_base_ref()
    └─ non approuvé  → "chore: ticket-XXX — unapproved work (<raison>)"
    (+ un second commit séparé pour la comptabilité vibe-ide :
     statuts de tickets et pipeline-log, jamais sous le message du ticket)
15. DB : finish_run(run_id, rounds, approved, final_status)
16. PipelineResult { ticket_id, final_status, rounds, approved, branch, commit_sha }
17. OrchestratorEvent.PIPELINE_DONE envoyé via WebSocket
```

**Invariants** (voir ADR-018) :

- Le commit est conditionné à la **réussite** de la création de branche : si le
  projet n'est pas un dépôt git, le pipeline continue sans committer plutôt que de
  committer sur une branche arbitraire.
- Seul un ticket **approuvé** fait avancer la ref de base. Le travail rejeté reste
  sur sa branche et ne contamine jamais le ticket suivant.
- Un fichier non suivi déjà présent au démarrage du run n'est jamais balayé dans le
  commit du ticket : il ne vient pas du codeur.

## Couche SQLite (ticket-015)

SQLite est une couche **cache/historique** — les fichiers Markdown restent la source de vérité (ADR-003).

```sql
-- Enregistre chaque exécution de pipeline
CREATE TABLE pipeline_runs (
    id           TEXT PRIMARY KEY,   -- UUID
    project_id   TEXT NOT NULL,
    ticket_id    TEXT NOT NULL,
    started_at   TEXT NOT NULL,      -- ISO 8601
    finished_at  TEXT,
    rounds       INTEGER,
    approved     INTEGER,            -- 0 ou 1
    final_status TEXT                -- "done" | "blocked"
);

-- Chaque event WebSocket émis pendant le pipeline
CREATE TABLE agent_events (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id    TEXT NOT NULL REFERENCES pipeline_runs(id),
    type      TEXT NOT NULL,         -- "agent_started" | "agent_token" | ...
    agent     TEXT,                  -- "codeur" | "reviewer" | null
    data_json TEXT,
    ts        TEXT NOT NULL
);
```

WAL mode activé pour éviter les locks en écriture concurrente.
`vibe_ide.db` configurable via `IDE_DB_PATH` (default: `vibe_ide.db` à la racine du projet).

## Structure des fichiers de tickets

```
projects/{project_id}/tickets/
  todo/         ← prêts à être pris en charge
  in-progress/  ← codeur en cours
  in-review/    ← reviewer en cours
  done/         ← approuvés
  blocked/      ← 3 tours sans approbation
  archive/      ← > 30 jours en done
```

Chaque ticket = fichier Markdown avec frontmatter YAML :
```yaml
---
id: ticket-007
title: Frontend scaffold — Vite + React + Tailwind
type: feat          # feat | fix | chore | design | docs
status: todo
priority: high      # critical | high | medium | low
agent: codeur
depends_on: []
created: 2026-06
github_issue_url: https://github.com/...  # optionnel
---
Corps du ticket en Markdown...
```

## OrchestratorEvents (WebSocket)

Les clients WebSocket reçoivent des `OrchestratorEvent` au format JSON :

```json
{
  "type": "agent_started | agent_token | agent_tool_use | agent_done | branch_created |
           ticket_status_changed | test_result | security_audit_started |
           security_audit_done | validation_done | doc_updated | commit_created |
           pipeline_done | error",
  "agent": "codeur | reviewer | testeur | securite | validateur | doc-updater | null",
  "ticket_id": "ticket-007",
  "data": { "round": 1, "token": "def foo", "status": "in-progress", "approved": true },
  "timestamp": "2026-06-20T14:30:00Z"
}
```

## Agents disponibles

| Rôle | Modèle | Usage |
|------|--------|-------|
| `codeur` | claude-sonnet-4-6 | Implémente les tickets feat/fix |
| `reviewer` | claude-sonnet-4-6 | Valide le code produit |
| `orchestrateur` | claude-sonnet-4-6 | Décompose les tickets complexes |
| `architect` | claude-sonnet-4-6 | Analyse architecturale |
| `project-creator` | claude-sonnet-4-6 | Crée de nouveaux projets |
| `github-sync` | — (pas de LLM) | Synchronise GitHub Issues → tickets |

## Communication inter-agents

Les agents ne se parlent pas directement.
L'Orchestrateur :
1. Passe le résultat du Codeur comme contexte au Reviewer
2. Injecte les feedbacks reviewer précédents dans le contexte du Codeur (tour suivant)
3. Décide du routing selon le verdict (`APPROVED` / `CHANGES_REQUESTED`)
4. Logue chaque transition dans `projects/{id}/memory/pipeline-log.md`
5. Persiste chaque run et event dans SQLite

## Mémoire des projets

```
projects/{project_id}/memory/
  decisions.md      ← ADRs, décisions d'architecture
  stack.md          ← versions, commandes, ports
  pipeline-log.md   ← historique des pipelines (auto-généré par l'Orchestrateur)
```

## Ajout d'un nouveau type d'agent

1. Créer `agents/prompts/{role}.md` avec le system prompt
2. Ajouter l'entrée dans `projects/{project_id}/agents.json`
3. Ajouter le role dans l'enum `AgentRole` (`models/agent.py`)
4. Si pipeline custom : modifier `Orchestrator.run_pipeline()`

Pas besoin de modifier le reste du code.
