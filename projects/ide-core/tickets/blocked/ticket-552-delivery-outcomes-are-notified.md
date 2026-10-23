---
agent: codeur
created: 2026-10-23
depends_on: []
estimated_days: 0.5
id: ticket-552
plan: true
pr_number: null
priority: medium
status: blocked
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
- [ ] `streamState.ts` traite `ci_merge_blocked` et `ci_watcher_blocked`, et un test le vérifie pour chacun
- [ ] `notificationsPour` de `lib/notifications.ts` produit une notification « mergée » sur `ci_merge_done`, et un test le vérifie
- [ ] `notificationsPour` produit une notification qui contient la raison sur `ci_merge_blocked` et sur `ci_watcher_blocked`, et un test le vérifie
- [ ] Un test montre qu'aucune de ces notifications ne part quand le projet est affiché et la fenêtre visible

## Ce que ça ne fait pas
- Ne touche pas au backend.