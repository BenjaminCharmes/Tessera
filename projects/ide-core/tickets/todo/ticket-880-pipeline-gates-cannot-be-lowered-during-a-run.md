---
agent: codeur
created: 2026-11-06
depends_on: []
estimated_days: 0.5
id: ticket-880
pr_number: null
priority: high
status: todo
title: A pipeline gate cannot be lowered while any run is live, and every lowering is logged
type: feat
---

# ticket-880 — Une porte du pipeline ne s'abaisse pas pendant un run

## Objectif

Même si le jeton de session fuyait, aucune requête ne peut couper l'audit,
le validateur ou le testeur, monter l'autonomie, autoriser le merge sans CI
ou changer la commande de test d'un projet pendant qu'un agent tourne.

## Contexte

Audit externe du 06/11. `PATCH /api/v1/projects/<id>/pipeline`
(`backend/src/tessera/routers/projects/pipeline.py`) accepte tous ces
changements sans condition, et les routes d'écriture de
`backend/src/tessera/routers/agent_admin.py` de même pour les rôles. Entre
deux runs, aucun processus d'agent n'existe : refuser pendant un run ferme la
fenêtre où un agent pourrait le faire.

## Solution proposée

- Une fonction pure `abaisse_une_porte(actuel, demande) -> list[str]` rend les
  champs qui abaissent une porte : `securite_enabled`, `validateur_enabled`
  ou `testeur_enabled` qui passent à `false`, `autonomy` qui monte dans
  `commit < pr < merge`, `merge_without_ci` qui passe à `true`,
  `test_command` modifiée.
- `PATCH …/pipeline` rend 409 si cette liste n'est pas vide et qu'**un run
  est vivant sur n'importe quel projet** (le registre des runs vivants), pas
  seulement sur celui-ci. Un abaissement accepté s'écrit en `warning`
  `porte_abaissee` avec le projet et les champs.
- Les écritures de rôles d'`agent_admin.py` (PUT, POST, DELETE) rendent 409
  pendant un run vivant.

## Critères d'acceptation

- [ ] Un test de `backend/tests/test_pipeline_portes.py` vérifie
      `abaisse_une_porte` sur chacun des six champs, et qu'une hausse
      (`securite_enabled` → `true`, `autonomy` `merge` → `pr`) n'en rend
      aucun.
- [ ] Un test vérifie qu'avec un run vivant sur un **autre** projet,
      `PATCH {securite_enabled: false}` rend 409.
- [ ] Un test vérifie qu'avec un run vivant, `PATCH {securite_enabled: true}`
      rend 200.
- [ ] Un test vérifie que sans run vivant, `PATCH {autonomy: "merge"}` rend
      200 et journalise `porte_abaissee`.
- [ ] Un test vérifie qu'un `PUT` d'`agent_admin.py` rend 409 pendant un run
      vivant.

## Dépendances

Aucune.

## Estimation

Une demi-journée.

## Risques

Benjamin ne peut plus baisser une porte depuis l'interface pendant une file :
il attend la fin de la file ou l'arrête. C'est voulu.
