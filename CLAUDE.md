# CLAUDE.md — Tessera

Tu travailles sur **Tessera** : un IDE multi-projets avec orchestration d'agents IA,
auto-hébergé — l'IDE se construit lui-même. `projects/ide-core/` porte les tickets,
la mémoire et les décisions qui guident sa construction.

## Contexte toujours chargé

@projects/ide-core/CLAUDE.md
@projects/ide-core/memory/decisions.md

Importés, pas seulement recommandés : les ADR sont des contraintes qui tiennent en
permanence, alors qu'un skill décrit *comment* faire une tâche et se charge à la
demande. Côté produit, `decisions.md` part aussi dans chaque appel d'agent, jusqu'à
18 par ticket : c'est pourquoi le skill `write-adr` impose un budget.

Ce fichier a le sien, mesuré par `test_consignes_coherentes.py` : chaque ligne y
concurrence les autres. Une règle qui a son skill ou son ADR n'est pas recopiée ici.

---

## Stack décidée

- **Backend** : Python 3.11+, **FastAPI**, Anthropic SDK et Agent SDK, **uv** (ni
  pip ni poetry). Pas de framework agent externe (LangChain, CrewAI).
- **Frontend** : TypeScript strict, **React 19** (hooks uniquement), **Tailwind CSS
  v4** — configuré dans le `@theme` de `index.css`, sans `tailwind.config.ts` —,
  **Monaco**, **Vite**.
- **Desktop** : **Tauri v2**, pas Electron.
- **Échanges** : HTTP pour lancer, une WebSocket d'observation pour suivre les runs
  (ADR-041). Tickets en Markdown avec frontmatter YAML.
- **Persistance** : SQLite via `aiosqlite` ; les tickets restent des fichiers,
  lisibles sans l'IDE.

---

## Structure du monorepo

```
tessera/
  CLAUDE.md              ← ce fichier (constitution globale)
  CLAUDE.local.md        ← overrides locaux (gitignore)
  .claude/               ← config Claude Code (skills, commands)
  projects/              ← tous les projets gérés par l'IDE
    ide-core/            ← projet bootstrap (l'IDE se construit lui-même)
  agents/prompts/        ← system prompts du produit, par rôle
  backend/               ← orchestrateur Python/FastAPI
  frontend/              ← UI React/TypeScript
  docs/                  ← documentation architecture
```

---

## Conventions de code

**Python** — type hints partout ; dataclasses ou Pydantic v2 ; `async/await` dans
FastAPI ; `snake_case`. Docstrings en anglais, commentaires en français (ADR-044).

**TypeScript** — `strict: true`, jamais de `any` ; composants en PascalCase,
fichiers en kebab-case ; hooks préfixés `use` ; pas de `console.log`, le logger
structuré.

**Git**
- Commits **et titres de PR** en anglais, Conventional Commits (ADR-044).
- Une branche par ticket : `ticket-XXX-description-courte`.
- `ticket-XXX` → PR vers `develop` (squash) → PR de `develop` vers `main`
  (**merge commit, jamais squash** : un squash réécrit les SHA et fait diverger
  les deux branches). Pas de commit direct sur `main` ni sur `develop`.
- Stager les fichiers nommément, **jamais `git add -A`** (balaie les projets
  importés dans `projects/`).
- **Aucune attribution à un outil d'IA**, ni trailer ni mention.

Le détail opératoire est dans le skill `ticket-workflow`.

---

## Configuration Claude Code (`.claude/`)

À ne pas confondre avec `agents/prompts/`, les prompts **du produit**.

```
.claude/
  skills/<nom>/SKILL.md   ← workflows, chargés à la demande par Claude
  commands/<nom>.md       ← slash commands, tapées par l'utilisateur
  settings.local.json     ← préférences personnelles (gitignoré)
```

Slash commands : `/new-ticket`, `/run-tessera`, `/ship`. Un skill se charge quand
sa `description` correspond à la tâche ; une slash command se tape. Un skill
ajouté en session n'est visible qu'à la suivante.

Skills disponibles : `brainstorming`, `writing-plans`,
`test-driven-development`, `code-review`, `verification-before-completion`,
`new-ticket`, `ticket-workflow`, `write-adr`, `run-tessera`.

Ces skills servent au développeur. Un agent du produit ne voit que ceux que son
rôle déclare dans `agents.json` (ticket-242). Les plugins installés restent une
inspiration, pas une dépendance : un clone neuf doit disposer de tout ce qui
précède.

---

## Règles pour les agents

1. **Lire le ticket complet** avant de coder
2. **Tenir le statut du ticket à jour** (todo → in-progress → done), dossier et champ
3. **Consulter les ADR avant toute décision d'architecture** — déjà en contexte :
   les ignorer est un choix, pas un oubli
4. **Écrire dans `memory/decisions.md`** toute décision d'architecture non triviale
5. **Ne jamais modifier** `CLAUDE.md` sans ticket explicite pour le faire
6. **Préférer des petits fichiers** (<200 lignes)
7. **Un test par fonction publique** au minimum
8. **Aucune trace d'écriture par IA** — commits, PR, commentaires, fichiers
   générés : ce que l'IDE écrit atterrit dans le dépôt de l'utilisateur

---

## Où en est le produit

Le détail est dans `projects/ide-core/tickets/done/`, les contraintes dans
`decisions.md`. Ceci ne dit que ce qu'il faut savoir pour ne pas reconstruire
l'existant.

**Ce qui marche**
- Pipeline codeur → testeur → sécurité → reviewer → validateur sur le **diff git
  réel**, une branche et un commit par run (ADR-018) ; documentation par lot en fin
  de file (ADR-035)
- Trois modes de run : un ticket, une file, autonome
- Livraison enchaînée après approbation — rebase, PR, CI, merge — jusqu'où le projet
  l'autorise (ADR-029, ADR-030) ; un conflit se tente et se relit (ADR-033)
- Artefacts hors des dépôts clients par défaut (ADR-021, ADR-023) ; les agents ne
  touchent pas à git (ADR-027) ni hors de leur projet (ADR-031)
- Registre d'agents, modèle par rôle, coûts et quota d'abonnement réel

**Ce qui n'existe pas**
- Ni comptes, ni multi-utilisateur, ni déploiement cloud — hors scope.
  `STATIC_TOKEN`, renseignée, exige un `Authorization: Bearer` partout ; vide (le
  défaut), l'API est ouverte : à ne servir que sur une interface de confiance
- Pas de résolution de conflit sans relecture, et ce n'est pas un manque
- Le contrôle d'écriture sur `Bash` attrape une erreur, pas une évasion (ADR-031)
