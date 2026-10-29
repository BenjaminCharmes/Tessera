---
agent: codeur
created: 2026-10-28
depends_on: []
estimated_days: 1
id: ticket-660
pr_number: 751
priority: medium
status: done
title: Done tickets are archived by hundreds, and every ticket lookup still finds
  them
type: feat
---

# ticket-660 — Archiver les tickets terminés sans les perdre de vue

## Objectif
Alléger `tickets/done/` sans qu'aucune recherche de ticket ne perde un ticket archivé.

## Contexte
`tickets/done/` d'ide-core compte plus de 600 fichiers. Pour un agent qui cherche
dans les tickets, ce sont autant de résultats parasites.

`TicketService.archive_old_tickets` (`services/ticket_service.py`) existe, mais
rien ne l'appelle. Et s'il était appelé, il casserait des choses : `_iter_active_files`
exclut `archive/`, si bien que `get_ticket` ne trouve plus un ticket archivé. Un
`depends_on` vers lui serait refusé (« introuvable » dans `trier_ajouts`, et au
lancement d'une file).

## Solution proposée
- L'archive range les tickets terminés par centaine :
  `tickets/archive/done/600-699/ticket-6XX-*.md`.
- `get_ticket`, la vérification des `depends_on` et `_next_n` lisent aussi
  l'archive. Les listes de l'interface et des agents ne la lisent pas.
- `POST /projects/{project_id}/tickets/archive` archive les tickets terminés dont
  le numéro est au moins cent sous le plus grand numéro du projet.

## Critères d'acceptation
- [ ] Un test vérifie que l'archivage range un ticket terminé dans `tickets/archive/done/<centaine>/`, et laisse en place un ticket non terminé ou trop récent
- [ ] Un test vérifie que `get_ticket` trouve un ticket archivé
- [ ] Un test vérifie qu'un ticket dont `depends_on` vise un ticket archivé est accepté dans une file
- [ ] Un test vérifie que `_next_n` compte les numéros de l'archive

## Ce que ça ne fait pas
- N'archive rien de lui-même : la route se lance à la main.