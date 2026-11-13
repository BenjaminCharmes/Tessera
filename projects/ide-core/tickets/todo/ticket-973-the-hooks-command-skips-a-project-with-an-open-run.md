---
agent: codeur
created: 2026-11-13
depends_on: []
estimated_days: 0.5
id: ticket-973
pr_number: null
priority: medium
status: todo
title: "The hooks command skips a project that has an open run"
type: fix
---

# ticket-973 — La commande `hooks` saute un projet dont un run est ouvert

## Objectif

Que la pose du hook `pre-push` ne bloque plus un run en cours.

## Contexte

Le 13/11 à 19:38 UTC, `scripts/tessera.ps1 hooks` (ticket-968) a posé le hook
dans tous les projets. Vigie ticket-101 tournait : l'empreinte des fichiers
protégés (ADR-084) a vu `.git/hooks/pre-push` changer pendant un appel
d'agent et a mis le run en `blocked`. La porte a fait son travail ; c'est la
pose qui est tombée au mauvais moment. `installer_sur_tous`
(`services/creation_projet/hook_pre_push.py`) ne regarde pas les runs.

## Solution proposée

1. `installer_sur_tous` reçoit l'ensemble des projets dont un run est ouvert
   (lu dans `pipeline_runs`, `finished_at IS NULL`, ou par le registre si le
   backend tourne) et saute ceux-là avec l'état `run_en_cours`.
2. La commande l'affiche (`vigie : run_en_cours`) et rend 1, pour qu'on la
   relance plus tard.
3. La pose à l'import et à la création ne change pas : aucun run n'existe
   encore.

## Critères d'acceptation

- [ ] Un test : un projet dont un run est ouvert n'a pas de hook posé, et son
      état est `run_en_cours`.
- [ ] Un test : les autres projets reçoivent leur hook dans le même appel.
- [ ] Un test : la commande rend 1 quand un projet a été sauté.

## Ce que ça ne fait pas

- Ne change pas l'empreinte (ADR-084) : un hook qui change pendant un run
  reste un motif de blocage.
