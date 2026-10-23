---
id: ticket-560
title: "The remaining tickets of a live queue count the ones added by append"
type: fix
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-23
---

# ticket-560 — Les tickets restants d'une file vivante comptent les ajouts

## Objectif
Que la pile de dossiers du Bureau (ticket-563) montre les tickets réellement
en attente dans une file, ajouts de `append` compris.

## Contexte
Conception : `docs/superpowers/specs/2026-10-23-vue-bureau-design.md`.
`GET /runs/{id}` d'un run vivant lit `run.file_restants`
(`statut_d_un_run_vivant`, `run_status.py`), que `run_executor.py` n'écrit que
sur `queue_progress`. `FileVivante.ajouter` et `retirer` (`file_vivante.py`)
modifient la file sans rien émettre : un ticket ajouté ne figure dans
`restants` qu'au prochain ticket traité, et un ticket retiré y reste.

## Solution proposée
`FileVivante` expose `restants() -> list[str]` : la file à partir du ticket
traité **inclus**, soit le sens de `restants` dans `queue_progress`. Pour un run
vivant qui porte une `FileVivante` (`run.file`), `statut_d_un_run_vivant` et
l'instantané du registre (`file_restants` dans le dictionnaire de
`run_registry.py`) rendent cette liste ; sans `file`, ils gardent
`file_restants`.

## Critères d'acceptation
- [ ] `FileVivante.restants()` rend la file du ticket traité à la fin, et la file entière avant le premier ticket, et un test le vérifie
- [ ] Un ticket ajouté par `POST /orchestrator/runs/{id}/append` figure dans `restants` de `GET /runs/{id}` sans qu'aucun `queue_progress` ne soit passé, et un test le vérifie
- [ ] Un ticket retiré par `.../remove` n'y figure plus, et un test le vérifie
- [ ] Un run vivant sans file (un seul ticket) garde `restants` tel qu'avant, et un test le vérifie
- [ ] L'instantané du registre porte la même liste que `GET /runs/{id}`, et un test le vérifie
- [ ] Le diff ne modifie aucun fichier de `frontend/`

## Ce que ça ne fait pas
- N'émet aucun événement sur `append` ou `remove` : le Bureau relit `GET /runs/{id}` (ticket-563).
- Ne change pas le statut d'un run terminé (`statut_en_base`).
