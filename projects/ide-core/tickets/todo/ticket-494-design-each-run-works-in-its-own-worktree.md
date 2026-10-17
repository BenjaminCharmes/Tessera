---
id: ticket-494
title: "Design how each run works in its own worktree, so no run ever writes where a human session works"
type: design
status: todo
pr_number: null
priority: medium
agent: architect
depends_on: []
estimated_days: 1
created: 2026-10-16
---

# ticket-494 — Concevoir un dossier de travail par run

## Objectif

Fixer, avant tout code, comment un run travaille dans son propre worktree,
sans jamais toucher le checkout où travaillent les sessions humaines, et sans
reproduire les accidents des essais passés.

## Contexte

Sur un projet en `git_root: ancestor` (ide-core), le run change de branche
et écrit **dans le dépôt même**. Le 16/10 : une session s'est ouverte sur une
branche de ticket avec des fichiers modifiés par le pipeline ; un ticket
écrit à la main dans `tickets/todo/` pendant un run a été commité par le
rangement du pipeline dans la PR du ticket en cours (#508) ; et un
redémarrage du PC a laissé le checkout sur une branche de run, à ranger à la
main.

Les essais de worktree ont coûté cher, et c'est ce que la conception doit
intégrer :
- une jonction `node_modules` dans un worktree a vidé le `node_modules` du
  dépôt (14/10) ;
- le hook d'écriture (ADR-031) ne suit pas les liens symboliques ;
- `uv` est refusé par le contrôle d'applications dans un worktree : les
  tests y tournent avec `PYTHONPATH=<wt>/backend/src` et le `python.exe` du
  `.venv` principal ;
- les chemins longs de Windows cassent `git worktree add` sur ce dépôt sans
  `core.longpaths` ;
- `.env`, `CLAUDE.md` et les fichiers ignorés par git n'existent pas dans un
  worktree neuf.

## Ce que la conception doit fixer

- Où vivent les worktrees, comment ils se nomment, quand ils se suppriment,
  et ce qu'il advient d'un worktree orphelin après un redémarrage.
- Ce que le projet déclare dans `agents.json` pour les peupler : copie
  (`.env`, `CLAUDE.md`), lien (`.venv`, `node_modules`, jamais pour ce qui
  s'édite), et ce que fait une entrée absente (journalisée, pas bloquante).
- Comment `test_command` et le hook d'écriture (ADR-031) tiennent compte du
  worktree, et ce que devient `git_root: ancestor`.
- Si deux runs sur le même dépôt deviennent possibles, ce qu'il advient de
  `RunLock` (ADR-038).

## Livrables

- Un ADR dans `memory/decisions.md`, et ses règles dans `contraintes.md`
  sous `## Proposées` si le ticket-493 est livré, sinon dans leur section.
- Les tickets d'implémentation, découpés, avec leurs dépendances.

## Critères d'acceptation

- [ ] L'ADR répond à chacun des points ci-dessus et cite les accidents passés
      comme contraintes
- [ ] Chaque ticket d'implémentation tient en moins d'une journée et nomme
      ses tests
- [ ] Aucun code n'est écrit par ce ticket
