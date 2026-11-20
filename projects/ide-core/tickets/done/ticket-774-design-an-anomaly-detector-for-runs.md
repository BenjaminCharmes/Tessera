---
agent: architect
created: 2026-11-03
depends_on: []
estimated_days: 1
id: ticket-774
pr_number: null
priority: medium
status: done
title: Design an anomaly detector that watches runs without stopping them
type: design
---

# ticket-774 — Concevoir un détecteur d'anomalies qui observe les runs sans les arrêter

## Objectif

Tessera signale de lui-même un run qui tourne en rond, qui dure ou coûte anormalement, ou
qui fait des allers-retours, au lieu d'attendre qu'un humain le remarque.

## Contexte

Le 03/11, il a fallu un humain pour voir : un ticket rejoué toute une nuit (testeur figé de
19 h à 7 h 48), trois tours perdus sur des doubles de test, deux livraisons coupées par le
réseau. Tessera n'a qu'un indicateur « figé ? ». Un IDE comparable a un détecteur qui
observe toutes les 5 minutes, sans rien arrêter : même appel d'outil 4 fois de suite ; durée
> 3 × la médiane des 20 dernières sessions de la même étape (minimum 10) ; coût > 3 × la
médiane ou ≥ 80 % du budget ; ≥ 3 corrections de revue sur un ticket ; session sans activité
depuis 15 minutes ; deux blocages consécutifs avec la même erreur.

## Ce que la conception doit fixer

- Quelles règles retenir, sur quelles données de Tessera (événements de run, `pipeline_runs`,
  appels d'agent enregistrés), et leurs seuils.
- Où il tourne (tâche de fond du backend), à quelle cadence, et comment une anomalie n'est
  signalée qu'une fois.
- Où elle s'affiche : notification, salle Tessera, Bureau (ADR-058 : un état rendu vient
  d'une donnée), journal.
- Ce qu'il ne fait jamais : arrêter, relancer ou modifier un run.

## Critères d'acceptation

- [ ] Une ADR au prochain numéro libre de `projects/ide-core/memory/decisions.md` répond à
      chacun des points ci-dessus et cite les incidents du 03/11
- [ ] Les tickets d'implémentation sont créés dans `projects/ide-core/tickets/todo/`, chacun
      tient en moins d'une journée et nomme ses tests (un test au-dessus et un en dessous de
      chaque seuil)
- [ ] Aucun code n'est écrit par ce ticket