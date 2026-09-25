---
id: ticket-180
title: "Le reviewer du ticket précédent reste affiché sous le codeur du suivant"
type: fix
status: done
pr_number: 35
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-25
---

# ticket-180 — Une file garde à l'écran l'état du ticket d'avant

## Objectif

Qu'un ticket qui démarre n'hérite pas de l'affichage du précédent.

## Contexte

Dans une file, quand le pipeline passe au ticket suivant et que le codeur
reprend la main au tour 1, le bloc **reviewer du ticket précédent** reste
affiché en dessous — avec son verdict `APPROVED` et le détail de sa revue.

À l'écran, ticket-013 semble avoir été approuvé par un reviewer qui n'a pas
encore tourné. C'est la pire forme d'erreur d'affichage : elle ne se voit pas
comme un défaut, elle se lit comme une information.

### La cause

Une file est **un** run (ADR-041), donc un seul état accumulé. Les drapeaux
d'affichage sont dérivés de la liste d'événements :

```tsx
const reviewerStarted = events.some(
  (e) => e.type === "agent_started" && e.agent === "reviewer",
);
```

`events` s'accumule sur toute la durée du run, donc sur **tous** les tickets de
la file. `reviewerStarted` reste vrai depuis le ticket d'avant, et
`reviewerContent` rend la dernière revue vue — celle du précédent.

`queue_progress` met bien à jour `ticketId` et l'avancement, mais laisse tout
le reste en place.

## Solution proposée

`queue_progress` annonce un **nouveau ticket** : l'état propre au ticket
repart à zéro — événements, agent courant, tour, verdict, résultat, question en
attente. Ce qui appartient au run, lui, survit : l'avancement de la file, le
quota, la branche.

## Critères d'acceptation

- [ ] Après un `queue_progress`, aucun événement du ticket précédent ne
      subsiste dans l'état
- [ ] L'avancement de la file, le quota et la branche survivent
- [ ] Le `ticketId` devient celui annoncé
- [ ] Le statut reste `running` — la file n'a pas cessé de tourner
- [ ] Une question en attente du ticket précédent ne survit pas
- [ ] `npx vitest run`, `tsc`, `eslint` et `npm run build` passent

## Dépendances

Aucune.

## Estimation

Moins d'une journée.

## Risques

Perdre l'historique du ticket précédent dans cet état. C'est voulu : il a déjà
été rapporté par son `pipeline_done`, et la carte de Supervision montre la
file depuis ticket-179.
