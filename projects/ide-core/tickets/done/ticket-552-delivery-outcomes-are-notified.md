---
agent: codeur
created: 2026-10-23
depends_on: []
estimated_days: 0.5
id: ticket-552
plan: true
pr_number: null
priority: medium
status: done
title: A merged PR, a red CI or a refused merge is notified
type: feat
---

# ticket-552 — La livraison est notifiée

## Objectif
Être prévenu quand une PR est mergée, quand sa CI échoue ou quand le merge
est refusé : c'est souvent là que le travail est vraiment terminé.

## Contexte
`lib/notifications.ts` (ticket-192) notifie une question, un run bloqué et
un run terminé. La phase 2 de livraison (`CIWatcher`, ADR-051) tourne après
la fin du run : `streamState.ts` reçoit déjà `ci_merge_done` (ticket-308),
mais `ci_merge_blocked` et `ci_watcher_blocked` ne produisent rien, et aucun
des trois ne déclenche de notification.

## Solution proposée
`notificationsPour` reçoit aussi les issues de livraison : « mergée »,
« CI rouge, PR laissée ouverte », « merge refusé » (avec sa raison). La
règle existante tient : rien vers le système quand le projet est déjà
affiché et la fenêtre visible. Le tour de plan vérifie que ces événements
atteignent bien le frontend après la fin du run ; sinon, il le dit et le
ticket s'arrête au constat.

## Critères d'acceptation
- [x] `notificationsPour` de `lib/notifications.ts` produit une notification « mergée » sur `ci_merge_done`, et un test le vérifie
- [x] `notificationsPour` produit une notification « non mergée » qui contient la raison quand `ci_merge_done` arrive avec `merged: false` et un `arret`, et un test le vérifie
- [x] Un test montre qu'aucune de ces notifications ne part quand le projet est affiché et la fenêtre visible

## Ce que ça ne fait pas
- Ne touche pas au backend.

## Correction du 23/10
`ci_merge_blocked` et `ci_watcher_blocked` ne sont que des messages du journal du
backend (`ci_watcher.py`), pas des événements de la WebSocket : le seul événement
est `ci_merge_done`, avec `merged: false` et la raison dans `arret`. Les deux
critères qui les nommaient étaient faux ; le codeur avait vu juste, le
validateur les a appliqués à la lettre. Livré à la main.
