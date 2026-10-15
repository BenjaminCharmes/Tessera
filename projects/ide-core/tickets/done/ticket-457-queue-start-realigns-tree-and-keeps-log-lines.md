---
agent: codeur
created: 2026-10-15
depends_on: []
estimated_days: 1
id: ticket-457
plan: true
pr_number: 476
priority: high
status: done
title: Starting a run puts the tree back on the base branch and keeps the uncommitted
  log lines
type: fix
---

# ticket-457 — Un run repart de la base sans geste à la main

## Objectif

Relancer une file ne demande plus de remettre l'arbre du projet sur sa
branche de base à la main.

## Contexte

make-your-call, 15/10 : après chaque run, l'arbre reste sur la branche du
dernier ticket et `memory/pipeline-log.md` est modifié, non commité, avec
des lignes absentes de `main`. Avant chaque relance (six fois dans la
journée), la session a dû copier le journal, le restaurer, revenir sur
`main`, `pull --ff-only`, puis recoller les lignes. Sans ça, le pull refuse,
ou la file part d'une base périmée. Le même `M pipeline-log.md` traîne dans
l'arbre de Tessera.

Les tickets 378 (arbre propre sur la base après livraison) et 406
(réalignement au départ d'un run) devaient couvrir ce cas ; le plan doit
établir ce qui leur échappe : livraison confiée au CIWatcher (phase 2 en
fond), lignes écrites dans le journal après le commit de tenue de livres,
ou refus du réalignement sur un arbre modifié
(`backend/src/tessera/services/git_workspace.py`).

## Solution proposée

Au départ d'un run, si l'arbre n'est pas sur la base ou si seul
`memory/pipeline-log.md` est modifié : mettre ces lignes de côté, revenir
sur la base, la réaligner sur le distant, puis réappliquer les lignes
absentes (union, sans doublon). Tout autre fichier modifié garde le refus
actuel.

## Critères d'acceptation

- [ ] Un test part d'un arbre resté sur la branche d'un ticket, avec
      `memory/pipeline-log.md` modifié, et vérifie que le run démarre sur la
      base réalignée
- [ ] Le même test vérifie que les lignes non commitées du journal sont
      toujours présentes, une seule fois chacune
- [ ] Un test vérifie qu'un autre fichier modifié bloque toujours le départ
- [ ] La raison pour laquelle 378 et 406 ne couvraient pas le cas est
      décrite dans la PR