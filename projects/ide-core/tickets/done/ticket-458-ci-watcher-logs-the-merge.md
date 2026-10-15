---
agent: codeur
created: 2026-10-15
depends_on: []
estimated_days: 0.25
id: ticket-458
pr_number: null
priority: medium
status: done
title: The CI watcher writes a pipeline-log line when it merges a PR
type: feat
---

# ticket-458 — Le CIWatcher écrit « PR #N mergée » dans le journal

## Objectif

On sait qu'une PR confiée au CIWatcher est mergée en lisant
`memory/pipeline-log.md`, sans interroger l'API ni GitHub en boucle.

## Contexte

make-your-call, 15/10 : pour savoir qu'une PR livrée par le CIWatcher est
mergée, la session interroge l'API et GitHub en boucle. Le CIWatcher
(`backend/src/tessera/services/ci_watcher.py`) écrit au journal ses échecs
(`_ecrire_ligne_log`), mais pour un succès seulement l'événement
`ci_merge_done`, visible sur la WebSocket et dans `tessera.log`.

## Solution proposée

Sur un merge réussi, écrire dans le `pipeline-log.md` du projet :
`[<projet>] <ticket> PR #N mergée (CI verte)`.

## Critères d'acceptation

- [x] Un test vérifie qu'un merge réussi par le CIWatcher écrit une ligne
      qui contient le ticket, « PR #N » et « mergée »
- [x] Un test vérifie qu'un échec n'écrit pas cette ligne