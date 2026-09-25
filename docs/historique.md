# Ce qui a été livré

Le détail par ticket est dans `projects/ide-core/tickets/done/`.
Cette page résume les grandes étapes.

### Phase 1–4 — Fondations + IDE fonctionnel ✅

| Feature | Status |
|---------|--------|
| Gestion de projets multi-projets | ✅ |
| Tickets Markdown avec frontmatter YAML | ✅ |
| Agent Codeur (Claude, streaming) | ✅ |
| Agent Reviewer (pipeline codeur→reviewer, max 3 tours) | ✅ |
| Orchestrateur multi-agents avec events WebSocket | ✅ |
| Mode autonome (traite les tickets en séquence) | ✅ |
| Agent GitHub Sync (Issues → tickets Markdown) | ✅ |
| Agent Project Creator (nouveau projet via conversation) | ✅ |
| Frontend React (ticket board, agent stream, Monaco) | ✅ |
| Shell desktop Tauri v2 (fenêtre native macOS) | ✅ |
| CI GitHub Actions (backend + frontend + e2e + tauri) | ✅ |
| Monaco branché sur le filesystem réel | ✅ |
| UI création de projet / ticket (modales + sidebar) | ✅ |
| SQLite persistence (historique des pipelines) | ✅ |
| Live ticket board (WS events → mise à jour temps réel) | ✅ |
| Panneau historique des pipelines (sidebar) | ✅ |
| UX polish (ErrorBoundary, toasts, skeletons, empty states) | ✅ |
| E2E tests Playwright (5 flows critiques) | ✅ |

### Phase 5 — Agents dynamiques + intégration GitHub ✅

| Feature | Status |
|---------|--------|
| Registre d'agents dynamiques (AgentRegistryService) | ✅ |
| API CRUD agents (GET/POST/DELETE /api/v1/agents/registry) | ✅ |
| Agent conversationnel agent-creator (nouveau agent via chat) | ✅ |
| UI gestion des agents (sidebar panel ⚙ + modale conversationnelle) | ✅ |
| Import projet local existant (modes symlink & copy) | ✅ |
| Agent project-analyzer (génération CLAUDE.md depuis le code) | ✅ |
| UI import de projet (3 étapes : source → analyse → validation) | ✅ |
| Agent planificateur (description NL → batch de tickets) | ✅ |
| UI « Planifier une évolution » + persistance batch | ✅ |
| Clone de repo GitHub dans le workspace | ✅ |
| Synchronisation bidirectionnelle tickets ↔ GitHub Issues | ✅ |
| Intégration GitHub Pull Requests (création + statut CI) | ✅ |
| Création automatique des agents manquants à la création de projet | ✅ |

### Phase 6 — Pipeline enrichi + qualité ✅

| Feature | Status |
|---------|--------|
| Mise à jour automatique de la documentation après pipeline (remplacée par lot, ADR-035) | ✅ |
| Agent testeur — exécution des tests dans le pipeline (pytest/npm/cargo) | ✅ |
| Agent validateur — vérification critère par critère des ACs du ticket | ✅ |
| Agent sécurité — audit OWASP automatique avant le reviewer | ✅ |
| Coverage tooling — pytest-cov backend + v8 frontend (74% backend) | ✅ |

### Phase 7 — Exécution réelle ✅

| Feature | Status |
|---------|--------|
| Provider Claude Agent SDK — fonctionne sur l'abonnement, sans crédits API | ✅ |
| Provider Anthropic API en fallback (Docker, CI, sessions non interactives) | ✅ |
| Les agents écrivent réellement les fichiers (outils fichier du SDK) | ✅ |
| Une branche git par run de pipeline, forkée d'une ref de base stable | ✅ |
| Le pipeline relit le **diff git réel**, plus la prose du codeur | ✅ |
| Commit automatique à chaque run (typé si approuvé, `chore:` sinon) | ✅ |
| Un ticket approuvé devient la base du ticket suivant (mode autonome) | ✅ |
| **Chat conversationnel** avec outils fichier, streaming et coût visible | ✅ |

### Phase 8 — Couverture et outillage ✅

| Feature | Status |
|---------|--------|
| Couverture des routers portée à 93,5 % | ✅ |
| Quota d'abonnement réel remonté par le fournisseur (ADR-020) | ✅ |
| Lancement d'un pipeline depuis le chat | ✅ |
| Outillage Windows (`doctor`, `scripts/tessera.ps1`) | ✅ |

### Phase 9 — Le projet appartient à l'utilisateur ✅

| Feature | Status |
|---------|--------|
| Lier un projet à un dépôt, ou en initialiser un | ✅ |
| Artefacts Tessera versionnés ou locaux, **par projet** (ADR-021, ADR-023) | ✅ |
| Le défaut échoue fermé : un projet importé garde ses artefacts chez lui | ✅ |
| Retirer un projet de l'IDE sans perdre ses fichiers | ✅ |
| Suivi par ticket, push et ouverture de PR — **jamais de merge** (ADR-022) | ✅ |
| Un projet doit être la racine de son propre dépôt (ADR-024) | ✅ |

### Phase 10 — Cockpit, dialogue et intégrité ✅

| Feature | Status |
|---------|--------|
| **Pivot cockpit** : l'IDE pilote la flotte, VSCode édite (ticket-065) | ✅ |
| Arbre de fichiers et éditeur en lecture seule | ✅ |
| **Dialogue pendant un run** : l'agent demande, l'utilisateur intervient | ✅ |
| Reprise sur hypothèse énoncée si personne ne répond (ADR-025) | ✅ |
| Cohérence visuelle : cinq familles de couleurs à rôle (ADR-026) | ✅ |
| **Les agents ne touchent pas à l'historique git** (ADR-027) | ✅ |
| Un run qui échoue à committer ne peut pas se dire## Structure du monorepo

```
Tessera/
├── .env.example              ← Template de configuration (copier en .env)
├── Makefile                  ← Commandes de lancement (make dev, make test...)
├── CLAUDE.md                 ← Constitution du projet pour les agents
│
├── backend/                  ← Orchestrateur Python/FastAPI
│   ├── pyproject.toml
│   ├── src/tessera/
│   │   ├── main.py           ← Point d'entrée FastAPI
│   │   ├── config.py         ← Settings (pydantic-settings, lit .env)
│   │   ├── models/           ← Pydantic models (Ticket, Agent, Project)
│   │   ├── routers/          ← Endpoints HTTP + WebSocket
│   │   ├── services/         ← Pipeline, git, livraison, documentation, GitHub…
│   │   │                        (le détail est dans docs/architecture.md)
│   │   └── agents/
│   │       └── github_sync.py      ← Sync bidirectionnelle tickets ↔ issues
│   └── tests/                ← pytest + respx
│
├── agents/
│   └── prompts/              ← System prompts de chaque agent (Markdown)
│       ├── codeur.md
│       ├── reviewer.md
│       ├── securite.md
│       ├── validateur.md
│       ├── doc-technique.md
│       ├── doc-fonctionnelle.md
│       ├── resolveur-conflit.md
│       ├── architect.md
│       ├── chat.md
│       ├── planificateur.md
│       ├── project-creator.md
│       ├── project-analyzer.md
│       └── agent-creator.md
│
├── projects/
│   └── ide-core/             ← Projet bootstrap (l'IDE se construit lui-même)
│       ├── CLAUDE.md
│       ├── agents.json
│       ├── tickets/
│       │   └── done/         ← 117 tickets terminés ✅ (Phases 1–10 complètes)
│       └── memory/
│           └── decisions.md  ← ADRs documentés
│
├── docs/
│   ├── architecture.md       ← Vue d'ensemble technique
│   ├── guide-utilisateur.md  ← Mode d'emploi
│   ├── configuration.md      ← Variables d'environnement
│   ├── api.md                ← Référence des endpoints
│   └── ticket-strategy.md    ← Stratégie hybride GitHub ↔ Markdown
│
└── frontend/                 ← React + TypeScript + Tailwind + Vite
```
