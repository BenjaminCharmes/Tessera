---
id: ticket-452
title: "The CI watcher stops with a message when a watched PR is in conflict"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 0.5
plan: true
created: 2026-10-15
---

# ticket-452 — Une PR en conflit ne reste pas muette dans le CIWatcher

## Objectif

Une PR surveillée par le CIWatcher qui devient non fusionnable produit une
ligne d'arrêt dans `pipeline-log.md`, débloque les tickets qui l'attendent
en échec, et ne reste pas en attente sans le dire.

## Contexte

make-your-call, 15/10 : la PR #14 (ticket-002), confiée au CIWatcher à
10:20, CI verte, est passée CONFLICTING après le merge d'une autre PR. Une
demi-heure plus tard : aucune ligne d'arrêt, rien de visible, la file a
continué (005, 006, 007).

`backend/src/tessera/services/ci_watcher.py` lance `livrer_phase_2`
(attente de CI puis `merge_quand_fusionnable` dans
`backend/src/tessera/services/github_service.py`, qui lève
`PRNonFusionnableError`). Le plan doit établir où la PR est restée : attente
de CI, attente de fusionnabilité (`mergeable` null), sémaphore du projet
occupé par une autre surveillance, ou exception avalée.

## Solution proposée

- Lire `mergeable` / `mergeable_state` pendant l'attente de CI : une PR
  `dirty` arrête la surveillance aussitôt, avec « PR #N en conflit avec
  <base> : à rebaser ».
- L'échec est enregistré comme un non-merge : les dépendants qui attendent
  ce ticket le reçoivent en échec (file interrompue, ADR-051).

## Critères d'acceptation

- [ ] Un test vérifie qu'une PR dont `mergeable_state` vaut `dirty`
      pendant l'attente de CI arrête la surveillance sans attendre le délai
- [ ] Un test vérifie que cet arrêt écrit une ligne dans `pipeline-log.md`
      qui contient le numéro de la PR et le mot « conflit »
- [ ] Un test vérifie qu'`attendre_merge` rend alors `False`
- [ ] Le lieu où la PR #14 est restée bloquée est décrit dans la PR
