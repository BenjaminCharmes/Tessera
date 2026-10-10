---
agent: codeur
created: 2026-10-07
depends_on:
- ticket-366
estimated_days: 1
id: ticket-367
pr_number: null
priority: high
status: done
title: Ticket cards read their PR status from one project-wide request
type: feat
---

# ticket-367 — Les cartes lisent l'état de leur PR dans une seule requête par projet

## Objectif

Ouvrir un projet ne déclenche plus qu'une requête pour l'état de toutes ses
PR, quel que soit le nombre de tickets.

## Contexte

`frontend/src/components/Sidebar/TicketCard.tsx` appelle
`api.github.getPrStatus` pour sa propre PR, au montage puis toutes les 30 s
(arrêt quand la PR est réglée, ticket-365 ; pause fenêtre cachée,
ticket-356). Avec 139 cartes sur ide-core, cela fait 139 requêtes à chaque
ouverture — 278 en développement, où React exécute deux fois chaque effet.
Le ticket-366 fournit `GET /projects/{project_id}/pr-statuses`, qui rend
l'état de toutes les PR d'un projet en une fois.

## Solution proposée

1. `frontend/src/lib/api.ts` gagne `api.github.getPrStatuses(projectId)`.
2. Un hook `frontend/src/hooks/usePrStatuses.ts` charge cette liste pour le
   projet actif et rend une table `ticket_id → statut`. Il ne rafraîchit
   (toutes les 30 s) que tant qu'une PR est `open`, et jamais fenêtre cachée
   (`useFenetreVisible`).
3. Les vues qui rendent des `TicketCard` (`Sidebar/TicketList.tsx`,
   `KanbanView`) passent à chaque carte son statut par une prop ; la carte ne
   fait plus aucun appel réseau pour sa PR. Le rendu du badge (lien
   « PR #N », info-bulle d'état, badge de CI) reste identique.

## Critères d'acceptation

- [ ] Un test de `frontend/src/hooks/usePrStatuses.test.ts` montre que le hook appelle `getPrStatuses` une seule fois pour un projet dont toutes les PR sont réglées, sans nouvel appel 30 secondes plus tard
- [ ] Un test de `frontend/src/hooks/usePrStatuses.test.ts` montre qu'avec une PR ouverte, le hook rappelle `getPrStatuses` après 30 secondes, et pas pendant que la fenêtre est cachée
- [ ] Un test de `frontend/src/components/Sidebar/TicketCard.test.tsx` montre qu'une carte rend l'info-bulle « PR mergée » et le badge « CI verte » à partir de la prop, sans appeler `getPrStatus`
- [ ] `frontend/src/components/Sidebar/TicketCard.tsx` n'appelle plus `api.github.getPrStatus`
- [ ] Les tests de `frontend/src/components/Sidebar/TicketCard.test.tsx` qui espionnaient `getPrStatus` sont adaptés à la nouvelle source, sans perdre les cas qu'ils couvraient (PR réglée, fenêtre cachée, erreur)

## Dépendances

ticket-366 (l'endpoint `pr-statuses`).

## Estimation

1 jour.

## Risques

Les tests du ticket-365 portent sur l'appel par carte, qui disparaît : leur
intention (une PR réglée n'est plus redemandée) passe au niveau du hook.

## Ce que ça ne fait pas

- Ne supprime pas l'endpoint par ticket côté backend.
- Ne limite pas le nombre de cartes affichées (ticket-368).