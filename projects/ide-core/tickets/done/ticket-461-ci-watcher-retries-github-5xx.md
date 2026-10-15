---
agent: codeur
created: 2026-10-15
depends_on: []
estimated_days: 0.5
id: ticket-461
pr_number: null
priority: medium
status: done
title: The CI watcher retries a GitHub 5xx instead of giving up the merge
type: fix
---

# ticket-461 — Un 5xx de GitHub se réessaie

## Objectif

Une indisponibilité passagère de GitHub (502, 503, 504) pendant la phase 2
ne fait plus abandonner le merge d'une PR à CI verte.

## Contexte

ide-core, 15/10, 13:16:04 : « [ticket-455] livraison : arrêt — PR #471 non
mergée : erreur inattendue : HTTPStatusError: Server error '503 Service
Unavailable' ». La CI était verte ; la PR a été mergée à la main.

`backend/src/tessera/services/ci_watcher.py` relit la PR après une
`httpx.TransportError` (ticket-405), mais un `httpx.HTTPStatusError` 5xx
tombe dans le `except Exception` et devient un échec définitif.

## Solution proposée

Dans les appels GitHub de la phase 2 (`backend/src/tessera/services/github_service.py`),
réessayer un 502, 503 ou 504 jusqu'à trois fois avec une attente croissante
(1 s, 2 s, 4 s ; attente injectable pour les tests). Au-delà, le
comportement actuel. Un 4xx ne se réessaie pas.

## Critères d'acceptation

- [ ] Un test vérifie qu'un 503 suivi d'un 200 sur la lecture de CI donne
      le verdict du 200
- [ ] Un test vérifie qu'un 503 suivi d'un succès sur le merge merge la PR
- [ ] Un test vérifie que trois 503 de suite gardent l'échec actuel
- [ ] Un test vérifie qu'un 403 n'est pas réessayé