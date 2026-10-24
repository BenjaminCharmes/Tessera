---
agent: codeur
created: 2026-10-23
depends_on: []
estimated_days: 1
id: ticket-559
pr_number: 633
priority: medium
status: done
title: A wait for an outside event and a conflict resolution are announced as events
type: feat
---

# ticket-559 — Une attente extérieure et une résolution de conflit sont annoncées

## Objectif
Que la salle de pause et la salle de réunion du Bureau (ticket-564) lisent un
événement, et que la santé d'un agent ne passe pas à « figé ? » pendant une
attente qui n'a rien d'un blocage.

## Contexte
Conception : `docs/superpowers/specs/2026-10-23-vue-bureau-design.md`. Deux
silences du backend :
- la boucle de file suspend sur `CIWatcher.attendre_merge` quand le ticket
  suivant dépend d'une PR en attente (`_attendre_si_dependant`,
  `_attendre_merge_et_syncer`, `services/orchestrator.py`) et n'émet rien : le
  run se lit « figé ? » au bout de 180 s (ticket-549) ;
- le résolveur de conflit (`resoudre` dans `livraison.py`, branché dans
  `routers/orchestrator.py`) travaille sans événement ; on n'apprend le conflit
  qu'après, par `livraison_done.conflits`.

## Solution proposée
Deux types dans `EventType` :
- `external_wait` — `{ reason: "dependency", waiting: true | false, ticket,
  pr_number }`. `waiting: true` avant la suspension, `waiting: false` après,
  **y compris** sur refus, exception ou annulation (`finally`). Rien n'est émis
  quand la file ne suspend pas.
- `conflict_resolution` — `{ phase: "started" | "ended", files, outcome }`.
  `started` quand le résolveur est appelé avec ses fichiers ; `ended` quand le
  rebase a tranché, avec `outcome: "resolved" | "cancelled"`.

Le CI de la phase 2 n'a pas d'événement à lui : le Bureau le déduit de
`livraison_done` et `ci_merge_done`, déjà émis.

## Critères d'acceptation
- [ ] Une file dont le ticket suivant dépend d'une PR en attente émet `external_wait` avec `waiting: true`, puis `waiting: false` une fois le merge signalé, et un test le vérifie
- [ ] Une attente qui se termine par un refus de merge, ou par une annulation de la tâche, émet quand même `waiting: false`, et un test le vérifie
- [ ] Une file dont aucun ticket restant ne dépend de la PR n'émet aucun `external_wait`, et un test le vérifie
- [ ] Un conflit de rebase confié à `resolveur-conflit` émet `conflict_resolution` `started` avec la liste des fichiers, puis `ended` avec `outcome`, et un test le vérifie pour `resolved` et pour `cancelled`
- [ ] Les deux événements sont persistés comme les autres événements du run et rejoués par `GET /runs/{id}/events`, et un test le vérifie
- [ ] Une résolution qui aboutit ouvre sa PR et ne se merge toujours pas seule (ADR-033) : les tests existants de la livraison passent sans modification
- [ ] Le diff ne modifie aucun fichier de `frontend/`

## Ce que ça ne fait pas
- N'ajoute rien à `frontend/types/api.ts` : l'union `EventType` côté frontend est mise à jour par le ticket-564.
- Ne change ni l'attente, ni sa durée, ni la décision de merger.