---
agent: codeur
created: 2026-11-06
depends_on: []
estimated_days: 1
id: ticket-874
plan: true
pr_number: null
priority: high
status: done
title: CIWatcher merge results are bound to their pull request and a second watch
  replaces the first
type: fix
---

# ticket-874 — Un résultat de `CIWatcher` est lié à sa PR

## Objectif

Un ticket relivré n'attend jamais le résultat de sa livraison précédente, et
l'attente d'une dépendance a un délai maximal.

## Contexte

Audit externe du 06/11, confirmé dans
`backend/src/tessera/services/livraison/ci_watcher.py` :

- tout l'état est indexé par `"project_id:ticket_id"`, sans numéro de PR ni
  SHA ;
- un second `surveiller` pour un ticket encore surveillé lance une seconde
  tâche ; le `finally` de la première retire le ticket de `_en_attente` et
  réveille l'événement partagé alors que la seconde tourne : `attendre_merge`
  rend le résultat de la première PR (ou `False`), et `en_attente()` ne liste
  plus un ticket encore surveillé ;
- `attendre_merge` rend `_resultats_merge[cle]` d'une livraison antérieure
  quand le ticket n'est pas (encore) enregistré, avant même de regarder le
  `pr_number` demandé ;
- `attendre_merge` attend un `Event` sans délai ; seule la borne de phase 2
  (`_timeout_phase2_s`) le limite indirectement, et l'attente du sémaphore
  du projet n'en a aucune. `attendre_si_dependant`
  (`backend/src/tessera/services/livraison/attente_dependance.py`) n'en
  ajoute pas.

## Solution proposée

- Indexer résultats et événements par `(project_id, ticket_id, pr_number)` ;
  `attendre_merge(project_id, ticket_id, pr_number)` ne rend que le résultat
  de cette PR.
- Un second `surveiller` du même ticket annule la tâche précédente et
  attend sa fin avant d'enregistrer la nouvelle ; le `finally` d'une tâche
  annulée ne touche pas à l'état de celle qui la remplace.
- `attendre_merge` prend un `timeout_s` (défaut : deux phases 2 plus une
  marge) et rend `False` à son expiration, en journalisant
  `attente_merge_expiree`.

## Critères d'acceptation

- [ ] Un test de `backend/tests/test_ci_watcher_relivraison.py` vérifie, avec
      des doubles, que deux `surveiller` successifs du même ticket (PR 1 puis
      PR 2) font rendre à `attendre_merge(…, pr_number=2)` le résultat de la
      PR 2, même quand la PR 1 finit après.
- [ ] Un test vérifie qu'après un second `surveiller`, `en_attente()` liste
      toujours le ticket tant que la PR 2 n'est pas finie.
- [ ] Un test vérifie qu'un résultat enregistré pour la PR 1 n'est pas rendu
      à `attendre_merge(…, pr_number=2)`.
- [ ] Un test vérifie qu'`attendre_merge` avec un `timeout_s` court rend
      `False` quand aucun résultat n'arrive.
- [ ] Les appelants d'`attendre_merge` passent le numéro de PR.

## Dépendances

Aucune.

## Estimation

Une journée.

## Risques

`attendre_merge` a plusieurs appelants (dépendances, livraison qui attend
les PR du projet, ADR-065) : tous doivent passer le numéro de PR.