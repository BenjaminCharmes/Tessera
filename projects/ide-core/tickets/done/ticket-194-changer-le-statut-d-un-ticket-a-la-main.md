---
id: ticket-194
title: "Changer le statut d'un ticket à la main, depuis la liste et le Kanban"
type: feat
status: done
pr_number: 58
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-26
---

# ticket-194 — Changer le statut d'un ticket à la main, depuis la liste et le Kanban

## Objectif

Qu'un ticket bloqué se remette en `todo`, qu'un ticket inutile passe en
`cancelled`, et qu'un ticket fait à la main passe en `done`, sans ouvrir
un éditeur de texte.

## Contexte

Le seul moyen de changer un statut hors pipeline est d'éditer le fichier
Markdown et de le déplacer de dossier — les deux, sinon l'UI et le fichier
divergent (skill `new-ticket`). Or `PATCH /projects/{id}/tickets/{tid}`
existe (`routers/tickets.py:90`), fait les deux, et `lib/api.ts` ne
l'appelle jamais. Le `KanbanView` affiche des colonnes qu'on ne peut pas
utiliser comme un Kanban.

## Solution proposée

- `api.ts` gagne `updateTicketStatus(projectId, ticketId, status)`.
- Dans `TicketCard`, un menu « Statut » avec les transitions permises ; dans
  `KanbanView`, glisser-déposer entre colonnes (HTML5 drag and drop, sans
  bibliothèque).
- Transitions permises à la main : `todo`, `blocked`, `done`, `cancelled`
  vers `todo` ; `todo` et `blocked` vers `cancelled` ; `todo` et `blocked`
  vers `done`. **Jamais** vers `in-progress` ni `in-review` : ces deux-là
  sont tenus par le pipeline, et un ticket `in-progress` sans run ferait
  croire à un run fantôme (ticket-177).
- Un ticket dont le run est en cours n'a pas de menu : le verrou d'ADR-038
  le tient.
- La liste et le Kanban se rafraîchissent depuis l'événement
  `ticket_status_changed` qui existe déjà, pas depuis la réponse du PATCH.

## Critères d'acceptation

- [ ] Un test vérifie que le menu ne propose pas `in-progress` ni
      `in-review`
- [ ] Un test vérifie qu'un ticket en cours de run n'a pas de menu
- [ ] Un test vérifie qu'un dépôt sur une colonne du Kanban appelle le PATCH
      avec le bon statut
- [ ] Un test vérifie que la liste se met à jour sur
      `ticket_status_changed`
- [ ] `npm run test` et `npm run build` passent

## Ce que ça ne fait pas

Pas d'édition du titre, de la priorité ni du corps : c'est un autre ticket,
et le backend n'a pas encore l'endpoint. Pas de changement de statut en lot.

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

Un statut changé à la main sur un ticket suivi par GitHub (`github_remote`)
ne remonte pas sur l'issue : à dire dans l'UI, pas à corriger ici.
