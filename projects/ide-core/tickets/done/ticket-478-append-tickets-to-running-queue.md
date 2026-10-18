---
agent: codeur
created: 2026-10-16
depends_on: []
estimated_days: 1
id: ticket-478
plan: true
pr_number: null
priority: medium
status: done
title: Tickets can be appended to a queue that is already running
type: feat
---

# ticket-478 — Ajouter des tickets à une file en cours

## Objectif

Des tickets posés pendant qu'une file tourne peuvent y être ajoutés en fin
de file, sans attendre sa fin pour en lancer une seconde.

## Contexte

souhaito, 16/10 : les tickets 015, 016 et 017, posés sur main pendant le
run, ont demandé une seconde file lancée à la main après la fin. Un second
`POST /run` sur le même projet prend un 409 (`RunLock`, ADR-038).

## Solution proposée

- `POST /api/v1/orchestrator/runs/{run_id}/append` avec `ticket_ids` : ajoute
  en fin de la file vivante ceux qui ne sont ni déjà dans la file, ni faits.
- La boucle de file relit sa liste à chaque passage au ticket suivant.
- Un ticket dont un `depends_on` n'est ni dans la file ni mergé est refusé
  dans la réponse.

## Critères d'acceptation

- [ ] Un test vérifie qu'un ticket ajouté pendant le premier ticket est
      exécuté après le dernier ticket d'origine
- [ ] Un test vérifie qu'un ticket déjà dans la file ou déjà fait n'est pas
      ajouté deux fois
- [ ] Un test vérifie qu'un `run_id` terminé rend 409
- [ ] Un test vérifie le refus d'un ticket dont la dépendance manque