---
id: ticket-665
title: "Startup recovery also cleans the repository of a run interrupted by a clean shutdown"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-10-28
---

# ticket-665 — La récupération nettoie aussi après un arrêt propre

## Objectif
Qu'après un arrêt du backend, quel qu'il soit, aucun checkout de projet ne reste
sale sur la branche d'un ticket (ADR-018, ADR-037).

## Contexte
Le 28/10, le backend s'est arrêté trois fois sur un Ctrl+C (corrigé par le
ticket-664). Un Ctrl+C est un arrêt **propre** : les runs en cours sont inscrits
en base avec `final_status = 'interrupted'` et une date de fin. Or la récupération
au démarrage (`solder_les_runs_orphelins`, puis `reprendre_depots_orphelins` dans
`services/reprise_orphelin.py`, appelés par le `lifespan` de `main.py`) ne
traite que les runs encore « en cours » (`finished_at` nul), c'est-à-dire ceux
d'un processus tué net. Les runs interrompus proprement passaient donc entre les
deux. Leurs checkouts restaient sur la branche du ticket, la fiche déplacée dans
`in-progress/` sans commit, et le `pipeline-log.md` modifié. Il a fallu nettoyer
à la main ceux de curio (ticket-021) et d'ide-core (ticket-617).

## Solution proposée
Au démarrage, `reprendre_depots_orphelins` reçoit aussi les runs dont
`final_status` vaut `interrupted` et dont le dépôt n'a pas encore été remis
d'aplomb : copie de travail encore sur la branche du ticket. Elle leur applique
la même reprise : fiche en todo, commit des changements comme travail non
approuvé, retour sur la base.

## Critères d'acceptation
- [ ] Un test vérifie qu'un run inscrit `interrupted`, dont le dépôt est resté sur la branche du ticket avec la fiche dans `in-progress/`, est repris au démarrage : fiche en todo, commit non approuvé, retour sur la branche de base
- [ ] Un test vérifie qu'un run `interrupted` dont le dépôt est déjà sur la branche de base n'est pas touché
- [ ] Un test vérifie que la reprise d'un run `interrupted` ne se fait qu'une fois, même si le backend redémarre deux fois

## Ce que ça ne fait pas
- Ne change pas la reprise des runs restés « en cours », déjà couverte (ticket-369).
