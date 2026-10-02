---
agent: codeur
created: 2026-10-02
depends_on:
- ticket-305
- ticket-306
estimated_days: 1
id: ticket-307
plan: true
pr_number: null
priority: high
status: blocked
title: A run frees its project once the PR is open, and a dependent ticket waits for
  the merge
type: feat
---

# ticket-307 — Un run libère son projet dès la PR ouverte

## Objectif

Brancher `livrer_phase_1` dans `run_pipeline`, et confier la phase 2 à
`CIWatcher`. Le verrou du projet (ADR-038) se libère dès la PR ouverte.
Un ticket qui dépend d'un autre attend son merge.

## Contexte

ADR-051. `run_pipeline` attend aujourd'hui toute la livraison.

Le ticket-302 empêche une file de s'empiler sur un ticket dont la CI est
rouge. Mais il ne couvre pas le cas d'une livraison qui s'arrête sur une
**exception** : un rebase refusé, ou un push impossible. Le 2026-10-02, le
289 et le 304 se sont ainsi retrouvés dans la PR du ticket suivant. Ce ticket
réécrit ce chemin : il doit couvrir ce cas.

Il n'existe pas de statut « PR ouverte » parmi les statuts de ticket, et il
ne faut pas en ajouter un : le modèle refuse toute valeur inconnue, et le
projet entier cesserait de se charger. L'attente se lit dans
`CIWatcher.en_attente()` (ticket-306).

## Critères d'acceptation

- [ ] Un test vérifie qu'un run approuvé appelle `livrer_phase_1`, confie la
      phase 2 à `CIWatcher.surveiller` sans l'attendre, puis émet
      `run_closed`
- [ ] Un test vérifie que `run_closed` est émis avant `ci_merge_done`
- [ ] Un test vérifie que, dans une file, un ticket dont `depends_on` nomme un
      ticket encore listé par `CIWatcher.en_attente()` attend avant de
      démarrer, puis démarre après son merge
- [ ] Un test vérifie qu'un ticket sans dépendance démarre depuis la base
      distante pendant que la PR du précédent attend sa CI
- [ ] Un test vérifie qu'après une livraison arrêtée par une exception, sans
      PR, le ticket suivant part de la base distante et non de la pointe du
      ticket précédent
- [ ] Les tests existants de `run_pipeline` (arbre sale, non approuvé)
      passent

## Dépendances

ticket-305, ticket-306.

## Périmètre

`backend/src/tessera/services/orchestrator.py` et ses tests.