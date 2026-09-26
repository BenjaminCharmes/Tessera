---
id: ticket-195
title: "Filtrer, trier et chercher dans les tickets"
type: feat
status: in-progress
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-26
---

# ticket-195 — Filtrer, trier et chercher dans les tickets

## Objectif

Retrouver un ticket parmi deux cents sans faire défiler.

## Contexte

`ide-core` a cent quatre-vingt-dix tickets, `demineur` une trentaine. La
liste (`TicketList.tsx`) et le Kanban n'offrent ni filtre, ni tri, ni
recherche. Le backend filtre déjà par statut (`GET /tickets?status=`,
`tickets.py:27`) ; tout le reste tient côté client, les tickets étant déjà
chargés en entier.

## Solution proposée

- Une barre au-dessus de la liste : champ de recherche (id, titre, corps),
  filtres par statut, type, priorité, agent ; tri par numéro, priorité,
  date de création, statut.
- Les filtres actifs sont mémorisés par projet avec le mécanisme du
  ticket-193, pour ne pas les re-poser à chaque ouverture.
- Le Kanban reçoit les mêmes filtres et le même champ de recherche : une
  seule source d'état, dans un hook `useFiltresTickets`.
- Un compteur « n sur N » dit ce que les filtres cachent : une liste vide
  sans explication se lit comme un projet sans tickets.
- Les tickets `done` et `cancelled` sont **repliés par défaut** dans la
  liste, avec un bouton pour les déplier : c'est ce qui rend la liste
  lisible sur `ide-core`.

## Critères d'acceptation

- [ ] Un test vérifie que la recherche sur un fragment d'id et sur un mot du
      titre rend les bons tickets
- [ ] Un test vérifie qu'un filtre par priorité combiné à un tri par numéro
      rend l'ordre attendu
- [ ] Un test vérifie que les `done` sont repliés par défaut et dépliables
- [ ] Un test vérifie que le compteur « n sur N » est juste
- [ ] Un test vérifie que les filtres survivent à un remontage
- [ ] `npm run test` et `npm run build` passent

## Ce que ça ne fait pas

Pas de recherche plein texte côté backend, pas de vues enregistrées.

## Dépendances

ticket-193 pour la mémorisation ; le reste est indépendant.

## Estimation

1 jour.

## Risques

Aucun notable.
