---
id: ticket-125
title: "Aligner prompts, docs et outillage sur ce que le produit fait"
type: docs
status: done
pr_number: 143
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-22
---

# ticket-125 — Aligner prompts, docs et outillage sur ce que le produit fait

## Objectif

Que les prompts produit, les consignes chargées à chaque session et la
documentation décrivent le pipeline tel qu'il tourne depuis ADR-017, 018 et
035.

Ce ticket **autorise explicitement** la modification de `CLAUDE.md` (racine)
et de `projects/ide-core/CLAUDE.md`, limitée aux points listés.

## Contexte

- `agents/prompts/codeur.md` demande de recopier « le code complet du
  fichier » dans la réponse et affirme que le code n'est pas dans son
  contexte : contrat d'avant ADR-017 (outils fichier) et ADR-018 (diff relu).
  Il ne mentionne pas que git en écriture lui est refusé (ADR-027).
- `agents/prompts/reviewer.md:73` : « Le code complet produit par le Codeur »
  au lieu du diff git.
- `doc-updater` survit dans `CLAUDE.md:180`, `docs/architecture.md`,
  `docs/guide-utilisateur.md:421`, `pipeline_stages.py:4` après ADR-035.
- Branche de chat : ADR-019, `chat_service.py` et `branch_cleanup.py`
  disent `chat/<horodatage>`, mais `GitWorkspaceService._branch_name` joint
  par un tiret et retire tout caractère hors alphanumérique — la branche
  réelle est `chat-<horodatage>`, comme l'écrivent `chat.md` et les docs.
  Conséquence : `_PREFIXES = ("ticket-", "chat/")` ne reconnaissait aucune
  branche de chat, et le nettoyage de ticket-070 les laissait toutes.
- Node : README « 20+ », guide « 24 LTS », `.nvmrc` 24, `frontend/Dockerfile`
  `node:20-slim` ; vitest 5 exige ≥ 22.12.
- `ci.yml` : `uv sync` sans `--locked` ; steps de couverture qui échouent sur
  une PR de fork (token lecture seule).
- `projects/ide-core/agents.json` porte `auto_merge_on_approve` (clef retirée
  au ticket-091) et `max_instances` (jamais lu).
- `agents/prompts/project-creator.md` recommande `orchestrateur`, `redacteur`,
  `planificateur` comme agents actifs : les deux premiers n'existent pas, le
  troisième est un service.
- `docs/historique.md` liste des prompts inexistants et « 38 tickets » pour
  117 ; `docs/api.md` répète une phrase ; `.vscode/settings.json` pointe un
  venv POSIX ; pas de `.dockerignore` frontend ; `Makefile run-windows`
  reproduit le motif `Start-Process` documenté comme cassé dans
  `tessera.ps1` ; `.gitignore:73` attribue un correctif au mauvais ticket.
- ADR-015 dit « 3 jobs parallèles » ; la CI en a 5, deux chaînés, et a raison.

## Solution proposée

1. Réécrire `codeur.md` : outils fichier, écrit sur disque, réponse = résumé
   court des fichiers touchés et des choix ; pas de git en écriture (le hook
   refuse). `reviewer.md` : « le diff git du run ».
2. Purger `doc-updater` des quatre emplacements ; `CLAUDE.md:180` nomme
   `doc-technique` et `doc-fonctionnelle` par lot (ADR-035).
3. `chat/` → `chat-` dans ADR-019, `chat_service.py` et `branch_cleanup.py`
   (`_PREFIXES`, avec un test qui reconnaît `chat-20260922-120000` et plus
   `chat/x`). Les prompts et les docs, eux, étaient justes.
4. Node 24 partout (`README.md`, `frontend/Dockerfile`), `.dockerignore`
   frontend.
5. `ci.yml` : `uv sync --locked --extra dev` ; steps de commentaire de
   couverture conditionnés à `github.event.pull_request.head.repo.full_name
   == github.repository`. Ne pas toucher aux autres steps (ticket-123 ajoute
   le lint).
6. `ide-core/agents.json` sans clefs mortes ; `test_consignes_coherentes.py`
   les traque aussi dans ce manifeste.
7. `project-creator.md` : agents réels (`codeur`, `reviewer`, `architect`).
8. `docs/historique.md`, `docs/api.md`, `.vscode/settings.json`, `Makefile`
   (`run-windows` supprimé, `.PHONY` complété), `.gitignore:73` corrigés.
9. ADR-015 amendé d'une ligne (skill `write-adr`) : cinq jobs, Tauri
   conditionnel.

Hors périmètre : `analyste-carriere.md` (agent d'un projet personnel figé
dans `BUILTIN_ROLES` — à trancher séparément), `tessera-detaches/` (données
utilisateur non suivies, à supprimer à la main), convention kebab-case,
`.env.example` et `--host` du Makefile (ticket-120).

## Critères d'acceptation

- [ ] `grep -rn "code complet\|contexte par défaut" agents/prompts` vide
- [ ] `grep -rn "doc-updater" CLAUDE.md docs backend/src` vide
- [ ] `grep -n "chat/" backend/src/tessera/services/branch_cleanup.py` vide,
      et une branche `chat-<horodatage>` est reconnue par le nettoyage
- [ ] `grep -n "node:" frontend/Dockerfile` → 24 ; `README.md` dit Node 24
- [ ] `ci.yml` contient `--locked` et la condition de fork sur les deux steps
      de couverture
- [ ] `grep -n "auto_merge_on_approve\|max_instances" projects/ide-core/agents.json`
      vide, et un test le verrouille
- [ ] `uv run pytest -q tests/test_consignes_coherentes.py` vert
- [ ] `uv run pytest -q`, `npm run typecheck` verts

## Dépendances
Aucune.

## Estimation
1 jour.

## Risques
`CLAUDE.md` est importé dans chaque session : garder les modifications aux
lignes citées.

## Ce que ça ne fait pas

- `agents/prompts/analyste-carriere.md` reste : c'est l'agent d'un projet
  personnel figé dans `BUILTIN_ROLES`, à trancher par un ticket à lui.
- `tessera-detaches/` n'est pas touché : données utilisateur non suivies,
  à supprimer à la main.
- Pas de convention kebab-case ajoutée ; `.env.example` et le `--host` du
  Makefile sont à ticket-120.
- `.gitignore:73` n'est pas modifié : l'historique (`8f61b6c`) montre que la
  destination des projets détachés est bien sortie du dépôt au ticket-078,
  l'attribution est juste.
- `docs/guide-utilisateur.md` disait déjà Node 24 ; seuls `README.md` et
  `frontend/Dockerfile` ont changé.
- `doc-updater` survit dans `decisions.md` (ADR-035) et dans les tickets
  terminés : ce sont des archives, pas des consignes.
