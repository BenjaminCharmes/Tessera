---
agent: codeur
created: 2026-10-06
depends_on: []
estimated_days: 0.5
id: ticket-361
pr_number: null
priority: high
status: done
title: A queue stops before a ticket whose dependency was approved but never delivered
type: fix
---

# ticket-361 — Une file s'arrête avant un ticket dont la dépendance n'a pas été livrée

## Objectif

Qu'un ticket ne démarre jamais dans une file tant qu'un ticket dont il dépend,
passé plus tôt dans la même file, n'a pas atteint la base.

## Contexte

Le 2026-10-05, trois projets (`habit-tracker`, `repo-health`,
`homelab-monitor`) ont tourné en file. Le jeton GitHub n'avait pas accès à
leurs dépôts : chaque ticket approuvé a vu sa livraison s'arrêter sur un 404
à la création de la PR (`livraison.arret`, `pr_number` à `None`). La file a
continué, et chaque ticket dépendant est parti de `main` **sans** le travail
de sa dépendance : un dashboard écrit sans l'API qu'il appelle, une API
écrite sans le collecteur qu'elle démarre (refusée trois tours sur des tests
rouges). Douze tickets à relancer.

`run_queue` (`backend/src/tessera/services/orchestrator.py`) n'examine les
dépendances des tickets restants que si `result.livraison.pr_number` est
renseigné : `_attendre_si_dependant` avec le `CIWatcher`, `_trouver_bloquant`
sans lui. Une livraison qui s'arrête **avant** la PR — conflit de rebase,
erreur d'API, autonomie `commit` — ne passe par aucune des deux branches.

ADR-051 dit pourtant que `depends_on` bloque le ticket suivant jusqu'au merge.

## Solution proposée

Dans `run_queue`, après un ticket approuvé dont la livraison n'a pas ouvert de
PR (`livraison` absente ou `pr_number` à `None`) : si un ticket restant le
déclare dans son `depends_on`, arrêter la file. Le résultat de ce ticket porte
une `livraison.arret` qui nomme le dépendant et la raison
(« ticket-003 dépend de ticket-002, qui n'a pas été livré : … »), comme le
fait déjà `_trouver_bloquant`. Les tickets restants **indépendants** ne
justifient pas de continuer seuls : la file s'arrête, comme pour un ticket
non approuvé, et le journal le dit.

## Critères d'acceptation

- [ ] Un test de `run_queue` : ticket A approuvé dont la livraison s'arrête
      sans PR, ticket B avec `depends_on: [A]` → B ne passe pas par
      `run_pipeline`
- [ ] Dans ce cas, la `livraison.arret` du résultat de A nomme B et A
- [ ] Le journal du pipeline écrit une ligne `file interrompue` qui nomme le
      ticket non livré
- [ ] Un test : A approuvé sans PR, B sans dépendance envers A → B s'exécute
      (le comportement actuel est gardé quand rien ne dépend de A)
- [ ] Les tests existants de la file avec PR et `CIWatcher` passent toujours

## Dépendances

Aucune.

## Estimation

0,5 jour.

## Risques

Une file en autonomie `commit` ne livre jamais : avec des `depends_on`, elle
s'arrêtera désormais au premier ticket dont un autre dépend. C'est le
comportement voulu — enchaîner sur une base qui n'a pas la dépendance produit
du travail à jeter — mais il change ce qu'on observe sur ces projets.

## Ce que ça ne fait pas

Ça ne fait pas attendre la file sur une livraison arrêtée, et ça ne la
relance pas : arrêter suffit, l'humain corrige la cause (jeton, conflit)
puis relance.