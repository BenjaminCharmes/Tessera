---
agent: codeur
created: 2026-10-15
depends_on: []
estimated_days: 0.5
id: ticket-449
pr_number: 460
priority: high
status: done
title: A CI the token cannot read stops the delivery at once, naming the missing permission
type: fix
---

# ticket-449 — Une CI illisible arrête la livraison tout de suite, avec la vraie raison

## Objectif

Quand le jeton GitHub de Tessera ne peut pas lire la CI d'un dépôt, la
livraison s'arrête aussitôt sur un message qui nomme la permission
manquante, au lieu d'attendre tout le délai de CI.

## Contexte

Signalé par make-your-call le 15/10 (PR #11, 08:38–08:54) : la CI était
verte en 1 min 22, mais la livraison a attendu 16 minutes, puis s'est
arrêtée sur « la CI de la PR #11 n'a pas rendu de verdict » et a interrompu
la file. Le jeton fine-grained lisait `pulls/11` (200), mais
`commits/<sha>/check-runs`, `commits/<sha>/status` et `actions/workflows`
répondaient 403 « Resource not accessible by personal access token » :
permissions Checks, Commit statuses et Actions absentes. C'est très
probablement aussi la « CI invisible » du portfolio (14/10).

Dans `backend/src/tessera/services/github_service.py`, `_get_ci_status`
rend `"none"` pour toute réponse différente de 200. Dans
`backend/src/tessera/services/livraison.py`, `_attendre_la_ci` traite
`"none"` comme une CI en retard tant que le dépôt déclare des workflows,
jusqu'au délai complet.

## Solution proposée

- `_get_ci_status` rend un état distinct, `"unreadable"`, sur une réponse
  403 ou 404 de `check-runs`.
- `_attendre_la_ci` rend ce verdict sans attendre.
- La livraison s'arrête alors avec un message du type « le jeton GitHub de
  Tessera ne peut pas lire la CI de ce dépôt (HTTP 403) : il lui faut les
  permissions Checks, Commit statuses et Actions en lecture ». La PR reste
  ouverte, le run n'échoue pas (ADR-030), et la porte reste fermée : rien ne
  se merge sans CI lue.
- `CIWatcher` (`backend/src/tessera/services/ci_watcher.py`) traite ce
  verdict de la même façon s'il l'appelle.

## Critères d'acceptation

- [ ] Un test vérifie qu'une réponse 403 de `check-runs` donne l'état
      `"unreadable"` dans `github_service.py`
- [ ] Un test vérifie que `_attendre_la_ci` rend `"unreadable"` au premier
      appel, sans dormir
- [ ] Un test vérifie que la livraison s'arrête alors sans merger, avec un
      `arret` qui contient « Checks » et le code HTTP
- [ ] Un test vérifie qu'une réponse 200 sans aucun check garde le
      comportement actuel (`"none"`, délai de grâce)

## Ce que ça ne fait pas

- Ne modifie pas le jeton : ajouter les permissions reste un geste de
  Benjamin.