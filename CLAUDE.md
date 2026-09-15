# CLAUDE.md — vibe-ide

Tu travailles sur **vibe-ide** : un IDE multi-projets avec orchestration d'agents IA,
construit de façon incrémentale et auto-hébergé (l'IDE se construit lui-même).

---

## Principe fondateur

Ce projet suit le pattern "self-hosting" : l'IDE est son propre premier projet.
Le dossier `projects/ide-core/` contient les tickets, la mémoire et les décisions
qui guident la construction de l'IDE lui-même.

Avant toute action, lis `projects/ide-core/CLAUDE.md` pour le contexte technique complet.

---

## Stack décidée

### Backend (orchestration & agents)
- **Python 3.11+** avec **FastAPI** pour l'orchestrateur HTTP/WebSocket
- **Anthropic SDK Python** pour les appels LLM
- **uv** comme gestionnaire de paquets (pas pip, pas poetry)
- Pas de framework agent externe (LangChain, CrewAI) — on construit le nôtre

### Frontend (UI de l'IDE)
- **TypeScript strict**
- **React 19** avec hooks uniquement (pas de class components)
- **Tailwind CSS v3**
- **Monaco Editor** pour l'éditeur de code embarqué
- **Vite** comme bundler

### Desktop shell
- **Tauri v2** (Rust sous le capot, UI React) — pas Electron
- Accès filesystem natif via les APIs Tauri

### Protocoles inter-couches
- **JSON-RPC 2.0** pour la communication UI ↔ orchestrateur
- **WebSocket** pour le streaming des réponses agents
- **Format ticket** : fichiers Markdown avec frontmatter YAML

### Persistence
- **SQLite** (via `aiosqlite`) pour la mémoire des agents et l'état des tickets
- Fichiers Markdown pour les tickets (lisibles sans l'IDE)

---

## Structure du monorepo

```
vibe-ide/
  CLAUDE.md              ← ce fichier (constitution globale)
  CLAUDE.local.md        ← overrides locaux (gitignore)
  .claude/               ← config Claude Code
    settings.json
  projects/              ← tous les projets gérés par l'IDE
    ide-core/            ← projet bootstrap (l'IDE se construit lui-même)
  agents/                ← définitions et prompts des agents
    prompts/             ← system prompts par rôle
  backend/               ← orchestrateur Python/FastAPI
  frontend/              ← UI React/TypeScript
  docs/                  ← documentation architecture
```

---

## Conventions de code

### Python
- Type hints partout, pas d'exception
- Dataclasses ou Pydantic v2 pour les modèles
- `async/await` partout dans FastAPI
- Nommage : `snake_case` pour tout
- Docstrings en anglais, commentaires en français si besoin de contexte métier

### TypeScript
- `strict: true` dans tsconfig, jamais de `any`
- Composants : PascalCase, fichiers : kebab-case
- Hooks custom préfixés `use`
- Pas de `console.log` en production (utiliser le logger structuré)

### Git
- Commits en anglais, format Conventional Commits : `feat:`, `fix:`, `chore:`,
  `docs:`, `refactor:`, `test:`
- Une branche par ticket : `ticket-XXX-description-courte`
- **Flux** : `ticket-XXX` → PR vers `develop` → PR de `develop` vers `main`
  - `main` — état publiable et branche par défaut du dépôt ; ne reçoit que des
    merges depuis `develop`
  - `develop` — intégration, cible par défaut de toutes les PR de ticket
  - Pas de commit direct sur `main` ni sur `develop`
  - `ticket → develop` : squash. **`develop → main` : merge commit, jamais
    squash** — un squash réécrit les SHA, ferait diverger les deux branches et
    priverait `main` de l'historique par ticket
- Stager les fichiers nommément, **jamais `git add -A`** (balaie les projets
  importés dans `projects/`)

Le détail opératoire est dans le skill `ticket-workflow`.

---

## Configuration Claude Code (`.claude/`)

`.claude/` contient la configuration **de Claude Code**, versionnée avec le
dépôt — à ne pas confondre avec `agents/prompts/`, qui contient les prompts
**du produit**, chargés par FastAPI.

```
.claude/
  skills/<nom>/SKILL.md   ← workflows, chargés à la demande
  settings.local.json     ← préférences personnelles (gitignoré)
```

Skills disponibles : `brainstorming`, `writing-plans`,
`test-driven-development`, `code-review`, `verification-before-completion`,
`new-ticket`, `ticket-workflow`, `write-adr`, `run-vibe-ide`.

**Chargement à la demande, jamais par `@`-import.** Un `@`-import dans ce
fichier est payé à chaque session ; un skill ne coûte que lorsqu'il sert. La
`description` du frontmatter est ce qui décide du déclenchement : elle dit
*quand* utiliser le skill, pas ce qu'il contient.

Les skills des plugins installés restent une source d'inspiration, pas une
dépendance : un clone neuf du dépôt doit disposer de tout ce qui précède.

---

## Règles pour les agents

1. **Toujours lire le ticket complet** avant de commencer à coder
2. **Mettre à jour le statut du ticket** (todo → in-progress → done) dès que l'état change
3. **Écrire dans `memory/decisions.md`** toute décision d'architecture non triviale
4. **Ne jamais modifier** `CLAUDE.md` sans ticket explicite pour le faire
5. **Préférer des petits fichiers** (<200 lignes) à de gros fichiers monolithiques
6. **Un test par fonction publique** au minimum

---

## État actuel (Phase 7 en cours)

- Backend, frontend et persistance SQLite sont en place et fonctionnels
- Pipeline complet codeur → testeur → sécurité → reviewer → validateur →
  doc-updater, orchestration WebSocket, intégration GitHub (issues/PRs/clone),
  registre d'agents dynamique — voir le tableau de fonctionnalités du `README.md`
- Les agents écrivent réellement sur disque (ADR-017) et chaque run de pipeline
  s'isole sur sa propre branche git, sur le diff réel (ADR-018)
- **Tickets ouverts** : `ticket-046` (décomposition de `run_pipeline`) et
  `ticket-048` (chat conversationnel) en `todo/`. Les tickets 045, 047 et 049
  sont livrés.
- Toujours pas d'auth et pas de déploiement cloud — hors scope pour l'instant
