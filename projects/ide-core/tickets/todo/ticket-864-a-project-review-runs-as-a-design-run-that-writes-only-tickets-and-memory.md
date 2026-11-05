---
id: ticket-864
title: "A project review runs as a design run that writes only tickets and memory"
type: feat
status: todo
priority: medium
agent: codeur
depends_on: [ticket-848, ticket-862, ticket-863]
estimated_days: 1
created: 2026-11-05
pr_number: null
---

# ticket-864 — Une revue de projet est un run `design` qui n'écrit que `tickets/**` et `memory/**`

## Objectif

Depuis l'interface, « relis ce projet et propose des changements » produit des tickets pour le
projet et des signalements pour ide-core, sans écrire de code, à coût plafonné.

## Contexte

ADR-080, spec §4. Aucun rôle ne relit un projet aujourd'hui ; `project-analyzer` n'écrit que le
`CLAUDE.md` d'un projet importé. Le rôle `architect` écrit déjà des tickets de suite : la
revue réutilise worktree, `RunLock` et livraison (ADR-041, ADR-056).

## Ce qu'il faut faire

- `POST /orchestrator/run` accepte `mode: "revue"` pour un projet ; la route crée le ticket de
  synthèse « Revue de <projet> » (type `design`, numéro par `numerotation.reserver`, ticket-848)
  et lance le rôle `architect` avec un brief de revue (lire le projet, ses ADR, ses tickets
  ouverts ; proposer, ne rien implémenter).
- Garde de fin de tour : tout fichier modifié hors `tickets/**` et `memory/**` met le run en
  `blocked` ; plus de 10 tickets créés : refus, rien n'est livré.
- Plafond de dépense : le plus petit de 3 $ et du plafond de run d'ADR-075, figé à l'ouverture ;
  coût estimé rendu par la route avant le lancement (ADR-020).
- `signaler` (ticket-863) ne donne pas plus de 5 signalements à ce run ; un projet
  `professional` n'en émet aucun.

## Critères d'acceptation

- [ ] `test_revue_projet.py::test_review_run_creates_a_design_ticket_with_a_reserved_number`
- [ ] `test_revue_projet.py::test_file_outside_tickets_and_memory_blocks_the_run`
- [ ] `test_revue_projet.py::test_eleventh_ticket_blocks_delivery`
- [ ] `test_revue_projet.py::test_spending_cap_is_the_smaller_of_three_dollars_and_the_run_cap`
- [ ] `test_revue_projet.py::test_professional_project_review_emits_no_report`
- [ ] `test_revue_projet.py::test_review_takes_the_project_lock`

## Ce que ça ne fait pas

N'implémente aucun des tickets qu'elle propose. Ne relit pas un projet occupé : 409 (ADR-038).
