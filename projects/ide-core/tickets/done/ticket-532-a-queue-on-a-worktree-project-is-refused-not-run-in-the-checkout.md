---
agent: codeur
created: 2026-10-22
depends_on: []
estimated_days: 0.5
id: ticket-532
pr_number: null
priority: high
status: done
title: A queue on a worktree project is refused instead of running in the checkout
type: fix
---

# ticket-532 — Une file sur un projet à worktree est refusée, pas lancée dans le checkout

## Objectif
Qu'un projet qui déclare `worktree` ne voie jamais un run écrire dans son
checkout, même lancé en file ou en autonome.

## Contexte
Triage ide-core du 22/10, après le premier run réel en worktree (kadoomi,
ticket-090). Dans `routers/orchestrator.py`, la branche worktree n'est prise
que si un `ticket_id` est fourni :
`if politique.worktree is None or not ticket_id:` construit un orchestrateur
**sans** worktree. Une file (`mode: queue`) ou un mode autonome lancé sans
`ticket_id` sur un projet à worktree tourne donc dans le checkout, en silence,
contre la règle acceptée d'ADR-056 (« jamais dans le checkout »). Avec un
`ticket_id` et un mode autre que `single`, la requête est déjà refusée en 422.

## Solution proposée
Échouer fermé : un projet dont la politique déclare `worktree` refuse tout
mode autre que `single` avec 422, `ticket_id` fourni ou non, avec le même
message qu'aujourd'hui. Les files par worktree (un worktree par ticket)
restent à concevoir.

## Critères d'acceptation
- [ ] Dans `routers/orchestrator.py`, un projet à worktree lancé en `queue` sans `ticket_id` reçoit une 422, et aucun orchestrateur n'est construit
- [ ] Même chose en mode `autonomous`
- [ ] Un test couvre chacun de ces deux cas
- [ ] Un test vérifie qu'un projet sans clé `worktree` se lance toujours en `queue` sans `ticket_id`

## Ce que ça ne fait pas
- Ne fait pas tourner une file dans des worktrees successifs : c'est un
  ticket de conception à part.