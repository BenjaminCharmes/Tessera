---
agent: codeur
created: 2026-11-06
depends_on: []
estimated_days: 0.5
id: ticket-883
pr_number: null
priority: medium
status: done
title: A capture run that times out kills its node process
type: fix
---

# ticket-883 — A capture run that times out kills its node process

## Objectif

Des captures qui dépassent leur délai ne laissent ni node ni Chromium vivants.

## Contexte

Trouvé par l'essai de seconde revue (ticket-846, `docs/essais/seconde-revue.md`) : le reviewer l'a relevé sur un commit classé sain, un humain l'a confirmé, et le défaut est toujours sur `develop` le 06/11. Entrée s12, ticket-432.

`capturer` (`backend/src/tessera/services/verification/captures.py`) borne l'exécuteur par `asyncio.wait_for(..., _DELAI_EXECUTEUR_S)`. `_lancer_le_script` attend `processus.communicate(...)` sans `try/finally` : à l'annulation, le processus continue de tourner.

## Solution proposée

Dans `_lancer_le_script`, entourer `communicate` d'un `try/except asyncio.CancelledError` qui appelle `processus.kill()` puis `await processus.wait()` avant de relancer l'annulation.

## Critères d'acceptation

- [ ] `_lancer_le_script` appelle `kill()` puis `wait()` sur le processus quand il est annulé.
- [ ] Un test (nouveau fichier `backend/tests/test_captures_delai.py`) lance un faux script qui dort, annule `_lancer_le_script` et vérifie que le processus n'est plus vivant.
- [ ] Ce test vérifie aussi que l'annulation se propage (`asyncio.CancelledError`).

## Dépendances

Aucune.

## Estimation

Une demi-journée au plus.

## Ce que ça ne fait pas

Ne revoit pas le reste du ticket d'origine : seulement le défaut confirmé.