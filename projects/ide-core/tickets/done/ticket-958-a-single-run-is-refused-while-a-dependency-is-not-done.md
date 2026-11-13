---
agent: codeur
created: 2026-11-12
depends_on: []
estimated_days: 0.5
id: ticket-958
pr_number: null
priority: high
status: done
title: A single run is refused while one of its dependencies is not done
type: fix
---

# ticket-958 — Un run single est refusé tant qu'une de ses dépendances n'est pas terminée

## Objectif

Qu'un ticket lancé seul ne parte pas sur une base qui n'a pas encore le
travail dont il dépend.

## Contexte

Signalement de la session Kadoomi, le 12/11. Kadoomi déclare `worktree` : il
ne se lance qu'en mode `single`. Le ticket-173 déclare
`depends_on: [ticket-171, ticket-172]`. Le 172 venait de finir en `blocked`,
et `POST /orchestrator/run` en mode `single` a accepté le 173 à 17:24 UTC
(run 71d6d970…) : 35 minutes et trois tours perdus, le validateur concluant
que le code attendu du 172 n'existait pas.

En mode `queue`, `file_vivante._dependance_manquante`
(`services/pipeline/file_vivante.py`) refuse un ticket dont une dépendance
n'est ni dans la file ni `done`. Le mode `single` (`routers/orchestrator.py`,
avant la réservation du run) ne fait aucun contrôle de ce genre.

## Solution proposée

1. Avant toute réservation, en mode `single`, lire le ticket demandé et
   chacune de ses dépendances avec la même lecture que la file (`_lire`,
   repli sur la base compris).
2. Une dépendance absente ou d'un autre statut que `done` refuse le run en
   **409**, avec le message « dépendance ticket-XXX non terminée
   (statut : …) ». Le projet reste libre.
3. `force: true` laisse passer, en journalisant, comme les autres refus
   d'emblée (ticket-477).

## Critères d'acceptation

- [ ] Un test : un ticket dont une dépendance est `blocked` est refusé en 409
      en mode `single`, et le message nomme la dépendance et son statut.
- [ ] Un test : une dépendance introuvable est refusée de la même façon.
- [ ] Un test : avec toutes ses dépendances `done`, le ticket part.
- [ ] Un test : `force: true` laisse partir le ticket malgré une dépendance
      non terminée.
- [ ] Un test : le refus ne réserve pas le projet (un second `POST` d'un autre
      ticket du même projet n'est pas refusé en 409 pour verrou).

## Ce que ça ne fait pas

- Ne change pas le mode `queue`, qui contrôle déjà ses dépendances.
- Ne traite pas les tests vitest qui tombent en `Timeout` sous charge dans le
  testeur (même signalement, ticket-172 de Kadoomi) : ce sont des tests du
  projet, à voir à part s'ils reviennent.