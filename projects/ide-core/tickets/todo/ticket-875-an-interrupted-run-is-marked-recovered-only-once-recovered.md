---
agent: codeur
created: 2026-11-06
depends_on: []
estimated_days: 0.5
id: ticket-875
pr_number: null
priority: high
status: todo
title: An interrupted run is marked recovered only after its recovery succeeded
type: fix
---

# ticket-875 — Un run interrompu n'est marqué repris qu'une fois repris

## Objectif

Un échec de la reprise d'un run interrompu laisse le run à reprendre : le
démarrage suivant retente, au lieu de l'oublier.

## Contexte

Audit externe du 06/11, confirmé dans
`backend/src/tessera/services/pipeline/reprise_orphelin.py` et
`backend/src/tessera/services/livraison/reprise_marqueur.py` : `marquer_depots_repris` pose `depot_repris_at`
**avant** `_reprendre_depot_seul`, qui avale toute exception et ne fait que
journaliser `reprise_erreur_git`. `runs_interrompus_a_reprendre` ne rend que
les runs dont `depot_repris_at` est nul : un commit raté (verrou git, hook)
laisse le dépôt sur la branche du ticket, arbre sale, et aucun démarrage ne
le reprendra.

## Solution proposée

Poser `depot_repris_at` seulement après un `_reprendre_depot_seul` réussi,
pour chaque dépôt. `_reprendre_depot_seul` rend un booléen de succès au lieu
d'avaler l'échec en silence ; un échec reste journalisé et le run reste à
reprendre.

## Critères d'acceptation

- [ ] Un test de `backend/tests/test_reprise_orphelin_echec.py` vérifie, avec
      un double git qui échoue au commit, que `depot_repris_at` reste nul pour
      ce run.
- [ ] Un test vérifie qu'au démarrage suivant, avec un double git qui
      réussit, le même run est repris puis marqué.
- [ ] Un test vérifie qu'une reprise réussie pose `depot_repris_at`.
- [ ] `_reprendre_depot_seul` déclare un type de retour `bool`.

## Dépendances

Aucune.

## Estimation

Une demi-journée.

## Risques

Une reprise qui échoue à chaque démarrage se journalise à chaque fois : c'est
voulu, le détecteur d'anomalies peut la voir.
