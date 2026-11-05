---
agent: codeur
created: 2026-11-05
depends_on: []
estimated_days: 1
id: ticket-849
pr_number: null
priority: high
status: done
title: A queue refuses tickets absent from origin base before it opens
type: fix
---

# ticket-849 — Une file refuse, avant d'ouvrir, un ticket absent de `origin/<base>`

## Objectif

Une file dont un ticket est introuvable ne démarre pas, au lieu de s'interrompre au milieu.

## Contexte

ADR-080. Le 05/11 à 16:18, la file s'est interrompue sur « Ticket introuvable : ticket-847 » :
le ticket n'existait que dans l'arbre de travail, pas sur la base d'où part le worktree
(ADR-056). `numerotation.noms_de_tickets_sur_la_base` sait déjà lister les tickets de
`origin/<base>`.

## Ce qu'il faut faire

- Avant d'ouvrir une file (et avant `append`, ticket-478), contrôler que chaque ticket nommé
  existe sur `origin/<base>` du projet ; pour un projet sans worktree, dans l'arbre.
- Absent : réponse 422 qui nomme les tickets en cause et dit de les pousser sur la base ; rien
  n'est ouvert, aucun verrou pris.
- Git illisible : la file s'ouvre comme avant (le contrôle ne ferme pas une porte qu'il ne peut
  pas juger — il n'en était pas une).

## Critères d'acceptation

- [ ] `test_file_preflight.py::test_queue_with_ticket_missing_from_base_is_refused_with_names`
- [ ] `test_file_preflight.py::test_refused_queue_takes_no_lock`
- [ ] `test_file_preflight.py::test_unreadable_git_opens_the_queue`
- [ ] `test_file_preflight.py::test_project_without_worktree_reads_the_tree`

## Ce que ça ne fait pas

Ne pousse rien sur la base. Ne change pas ce qui arrive à un ticket qui disparaît pendant la file.