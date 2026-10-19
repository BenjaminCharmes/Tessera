---
agent: codeur
created: 2026-10-18
depends_on: []
estimated_days: 1
id: ticket-504
plan: true
pr_number: 539
priority: medium
status: done
title: A ticket merged into the base branch while a queue runs can be appended to
  that queue
type: fix
---

# ticket-504 — Un ticket mergé pendant une file peut y être ajouté

## Objectif

`POST /orchestrator/runs/{id}/append` accepte un ticket qui vient d'arriver sur
la branche de base (merge d'une PR `chore: add ticket NNN`) pendant que la file
tourne, et la file l'exécute à son tour.

## Contexte

18/10, file ide-core e06c96b7 : le ticket-503 est mergé sur `develop`, puis
ajouté à la file. Réponse : `{"refuses":{"ticket-503":"ticket introuvable"}}`.
`trier_ajouts` (`file_vivante.py`) lit le ticket avec un `TicketService` posé
sur l'arbre de travail du projet ; pendant la file, cet arbre est sur la
branche du ticket en cours, partie de la base telle qu'elle était au démarrage.
Un ticket écrit après le lancement n'y est donc jamais. Or c'est le cas normal
d'usage du ticket-478 : on écrit un ticket (dans un worktree à part, jamais dans
le checkout du run), on le merge, on l'ajoute.

## Ce que la conception doit fixer (tour de plan)

- Où lire le ticket ajouté : `git show origin/<base>:<chemin>` après `fetch`,
  sans toucher l'arbre du run.
- Comment le ticket existe au moment de son tour : la branche du ticket part
  de la base à jour (fetch puis départ de `origin/<base>`), ce que le
  ticket-480 prépare déjà en fin de run.
- Ce qui reste refusé : un ticket absent aussi de `origin/<base>`.

## Critères d'acceptation

- [ ] Un test vérifie qu'un ticket présent seulement sur `origin/<base>` est
      accepté par l'ajout
- [ ] Un test vérifie que ce ticket, à son tour, part d'une branche qui le
      contient
- [ ] Un test vérifie qu'un ticket absent de l'arbre et de `origin/<base>`
      reste refusé avec « ticket introuvable »
- [ ] Un test vérifie que l'arbre de travail du run n'est ni modifié ni
      changé de branche par l'ajout