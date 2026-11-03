---
agent: codeur
created: 2026-11-03
depends_on:
- ticket-740
estimated_days: 1
id: ticket-741
pr_number: null
priority: high
status: done
title: A phase-one delivery stop marks the ticket blocked
type: fix
---

# ticket-741 — Un arrêt de livraison en phase 1 met le ticket en `blocked`

## Objectif

Un ticket approuvé dont la livraison s'arrête avant d'ouvrir sa PR se lit `blocked`
avec sa raison, pas `done`.

## Contexte

03/11, ticket-733 : approuvé, passé `done`, puis la livraison s'arrête (tests rouges
après rebase) sans PR. Le run finit `done`, la file le compte parmi les approuvés, et
rien ne signale qu'il n'est pas livré : seul le journal le dit.

La phase 2 bloque déjà le ticket sur une CI rouge (ADR-051), et la phase 1 le fait pour
une branche modifiée depuis l'approbation (`_bloquer_branche_modifiee`,
`backend/src/tessera/services/orchestrator.py`). Les autres arrêts de phase 1 sans PR —
rebase refusé, conflit non résolu, tests rouges après rebase, push refusé, échec
d'ouverture de PR — ne le font pas. ADR-030 reste vrai : le run n'échoue pas, seul le
statut du ticket change.

## Solution proposée

- Après `self._livrer`, quand `livraison.arret` est posé, sans `pr_number`, et que
  l'arrêt n'est pas l'arrêt voulu du niveau `commit` (`arret_niveau_commit`) : mettre
  le ticket en `blocked`, comme `_bloquer_branche_modifiee`, avec l'événement
  `ticket_status_changed`.
- Le résultat du run porte `final_status: blocked` dans ce cas.

## Critères d'acceptation

- [ ] Un test vérifie, avec des doubles, qu'un arrêt de phase 1 sans PR (tests rouges
      après rebase) met le ticket en `blocked` et émet `ticket_status_changed`
- [ ] Un test vérifie que l'arrêt du niveau `commit` laisse le ticket `done`
- [ ] Un test vérifie qu'une livraison qui ouvre sa PR laisse le ticket `done`
- [ ] Un test vérifie que le résultat du run porte `final_status` `blocked` après un
      arrêt de phase 1 sans PR

## Dépendances

ticket-740 (même zone de `livraison.py` / `orchestrator.py`).

## Estimation

1 jour.

## Risques

- Une PR orpheline (`pr_orpheline`) a un numéro : elle reste suivie par le
  CIWatcher, ce ticket ne la touche pas.