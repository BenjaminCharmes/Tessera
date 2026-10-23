---
id: ticket-553
title: "An agent suspected of being stalled is notified"
type: feat
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: ["ticket-549"]
estimated_days: 0.25
created: 2026-10-23
---

# ticket-553 — Un agent figé est notifié

## Objectif
Être prévenu quand un agent passe à « figé ? » (plus de 3 minutes sans
événement), au lieu de l'apprendre 20 minutes plus tard.

## Contexte
Le ticket-549 calcule la santé d'un agent côté frontend : travaille,
silencieux, question, figé ?. Les runs figés pendant la veille du PC ne se
voyaient qu'à l'arrêt par `agent_silence_max_s` (1200 s).

## Solution proposée
`notificationsPour` de `lib/notifications.ts` reçoit l'état de santé de
chaque run et produit une notification au **passage** vers « figé ? »,
une seule fois tant que l'agent n'est pas revenu à un autre état.

## Critères d'acceptation
- [ ] Un test montre une notification au passage de « silencieux » à « figé ? »
- [ ] Un test montre qu'un agent qui reste « figé ? » sur deux instantanés ne produit qu'une notification
- [ ] Un test montre qu'un agent revenu à « travaille » puis de nouveau « figé ? » produit une seconde notification
- [ ] Un test montre que rien ne part vers le système quand le projet est affiché et la fenêtre visible
