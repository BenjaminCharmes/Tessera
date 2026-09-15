# CLAUDE.md — vibe-ide

Tu travailles sur **vibe-ide** : un IDE multi-projets avec orchestration d'agents IA,
construit de façon incrémentale et auto-hébergé (l'IDE se construit lui-même).

---

## Principe fondateur

Ce projet suit le pattern "self-hosting" : l'IDE est son propre premier projet.
Le dossier `projects/ide-core/` contient les tickets, la mémoire et les décisions
qui guident la construction de l'IDE lui-même.

## Contexte toujours chargé

@projects/ide-core/CLAUDE.md
@projects/ide-core/memory/decisions.md

Ces deux fichiers sont importés, pas seulement recommandés à la lecture. Un
`@`-import coûte ~2000 tokens **une fois par session** — négligeable au regard
d'une décision d'architecture violée faute de la connaître.

À ne pas confondre avec le coût côté produit : `decisions.md` est aussi injecté
par le backend dans **chaque appel d'agent**, jusqu'à 18 par ticket. C'est là
que la longueur d'un ADR compte, et c'est pourquoi le skill `write-adr` impose
un budget. Les deux budgets sont distincts.

Les **skills** restent chargés à la demande : ils décrivent *comment* faire une
tâche donnée, alors que les ADR sont des contraintes qui doivent tenir en
permanence. C'est ce qui justifie l'import ici et pas là.

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
- **Aucune attribution à un outil d'IA** : ni `Co-Authored-By`, ni mention
  d'assistant dans un message de commit, un titre ou une description de PR

Le détail opératoire est dans le skill `ticket-workflow`.

---

## Configuration Claude Code (`.claude/`)

`.claude/` contient la configuration **de Claude Code**, versionnée avec le
dépôt — à ne pas confondre avec `agents/prompts/`, qui contient les prompts
**du produit**, chargés par FastAPI.

```
.claude/
  skills/<nom>/SKILL.md   ← workflows, chargés à la demande par Claude
  commands/<nom>.md       ← slash commands, tapées par l'utilisateur
  settings.local.json     ← préférences personnelles (gitignoré)
```

**Skills et slash commands sont deux choses différentes.** Un skill est chargé
par Claude quand sa `description` correspond à la tâche — il ne se tape pas.
Une slash command est une invite que l'utilisateur déclenche à la main
(`/run-vibe-ide`), et qui peut s'appuyer sur un skill. Les skills ajoutés
pendant une session ne sont visibles qu'au démarrage de la suivante.

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
3. **Consulter les ADR avant toute décision d'architecture** — ce sont des
   contraintes en vigueur, pas des archives. Ils sont importés plus haut, donc
   déjà en contexte : les ignorer est un choix, pas un oubli
4. **Écrire dans `memory/decisions.md`** toute décision d'architecture non triviale
5. **Ne jamais modifier** `CLAUDE.md` sans ticket explicite pour le faire
6. **Préférer des petits fichiers** (<200 lignes) à de gros fichiers monolithiques
7. **Un test par fonction publique** au minimum
8. **Ne jamais laisser de trace d'écriture par IA** dans ce qui est produit —
   commits, PR, commentaires, docstrings, fichiers générés. Ce que l'IDE écrit
   atterrit dans le dépôt de l'utilisateur, parfois celui d'un client : la
   provenance du code n'y a pas sa place

---

## État actuel (Phase 7 en cours)

- Backend, frontend et persistance SQLite sont en place et fonctionnels
- Pipeline complet codeur → testeur → sécurité → reviewer → validateur →
  doc-updater, orchestration WebSocket, intégration GitHub (issues/PRs/clone),
  registre d'agents dynamique — voir le tableau de fonctionnalités du `README.md`
- Les agents écrivent réellement sur disque (ADR-017) et chaque run de pipeline
  s'isole sur sa propre branche git, sur le diff réel (ADR-018)
- **Tickets 045 à 052 livrés** : pipeline sur diff réel, décomposition de
  `run_pipeline`, skills locaux, chat conversationnel, flux git `develop`,
  échecs bruyants sur prompt manquant, plafond de dépense par run
- **Phase 8 terminée** — couverture des routers (86 → 93,5 %), quota réel de
  l'abonnement, lancement de pipeline depuis le chat, outillage Windows
  (`doctor`, `scripts/vibe.ps1`), ADR chargés automatiquement
- **Phase 9 terminée** — liaison d'un projet à GitHub, artefacts versionnés ou
  locaux par projet (`.git/info/exclude`, ADR-021), retrait d'un projet sans
  perte de fichiers, suivi par ticket et ouverture de PR (ADR-022 : jamais de
  merge). Aucun ticket ouvert
- **Workflow allégé** : plus de PR ni d'attente de CI pendant cette phase, les
  commits vont directement sur `develop`. `main` reste le point de retour
- Toujours pas d'auth et pas de déploiement cloud — hors scope pour l'instant
