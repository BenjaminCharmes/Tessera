---
id: ticket-340
title: "A failed fetch of the base is retried, logged, and blocks a dependent ticket instead of forking it from a stale base"
type: fix
status: done
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-05
---

# ticket-340 — Un fetch de la base raté ne fait plus partir un ticket d'une base périmée

## Objectif

Qu'un ticket qui dépend d'un autre parte toujours d'une base qui contient son
merge, ou ne parte pas.

## Contexte

Démineur, 2026-10-05, d'après les reflogs : la PR #39 du ticket-033 est
mergée à 10:46:59 ; la branche du ticket-034 (`depends_on: ticket-033`) est
créée à 10:47:03 depuis `5f30d09`, la base d'avant ce merge ; la branche `main`
locale ne passe à `97869bc` qu'à 11:02:54, pendant la livraison du 034.
Approuvé, le 034 s'est arrêté sur un conflit dans `src/App.tsx`, et son
relancement l'a recodé de zéro (branche `stale/…`).

La base n'est pas figée pendant la file : `initialiser_base_ref` est rappelée
avant chaque ticket. Mais au démarrage du 034, son `git fetch` a échoué
(`base_ref_initialisee_locale` au journal), et elle s'est rabattue en silence
sur la branche locale, périmée, sans journaliser pourquoi.

## Solution proposée

- Le fetch de la base est retenté (trois tentatives, deux secondes d'écart).
- Un échec définitif journalise sa raison (`base_ref_fetch_echoue`).
- `initialiser_base_ref(exiger_distant=True)` rend une raison de blocage au
  lieu de se rabattre sur la base locale ; l'étape de création de branche
  l'exige quand le ticket déclare un `depends_on`.
- Sans `depends_on`, le repli local reste, comme le prévoit le ticket-285.

## Critères d'acceptation

- [x] Un test vérifie qu'un fetch qui échoue une fois est retenté et que la
      base suit le distant
- [x] Un test vérifie qu'avec `exiger_distant`, un distant illisible rend une
      raison qui cite l'erreur, sans fixer de base
- [x] Un test vérifie que, sans `exiger_distant`, le repli local reste et
      que l'erreur est journalisée
- [x] Un test vérifie que l'étape de création de branche bloque un ticket à
      `depends_on` quand le distant est illisible

## Ce que ça ne fait pas

La cause de l'échec du fetch du 034 n'est pas établie : le journal du backend
n'était pas horodaté, et ne disait pas l'erreur. Le second point est corrigé
ici.

## Dépendances

Aucune.

## Estimation

0,5 jour.
