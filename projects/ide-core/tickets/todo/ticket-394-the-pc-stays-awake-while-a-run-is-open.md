---
id: ticket-394
title: "The PC stays awake while a run is open, and may sleep again once the last run closes"
type: feat
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-10
---

# ticket-394 — Le PC reste éveillé tant qu'un run est ouvert

## Objectif

Qu'une file lancée le soir ne soit plus figée par la mise en veille
automatique du PC.

## Contexte

Sur trois nuits, la mise en veille a figé les runs d'affut, d'ide-core et de
vigie : `claude.exe` figé, « délai dépassé » du testeur deux fois (affut 008
le 2026-10-08, puis 020 le 2026-10-09), ticket bloqué au réveil, reprise à
la main. Signalé comme idée par la session qui pilote affut, le 2026-10-10.

Windows permet à un processus de demander au système de rester éveillé :
`SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)`, relâché par
`SetThreadExecutionState(ES_CONTINUOUS)`. L'écran peut s'éteindre ; seule la
veille du système est empêchée.

## Solution proposée

1. Un module `backend/src/tessera/services/eveil.py` expose `retenir()` et
   `relacher()`. Sous Windows, il appelle `SetThreadExecutionState` par
   `ctypes` ; ailleurs, ce sont des no-op journalisés une fois. Un échec de
   l'appel est journalisé, jamais levé.
2. `RunRegistry` (`backend/src/tessera/services/run_registry.py`) appelle
   `retenir()` quand il passe de 0 à 1 run ouvert (`ouvrir`) et `relacher()`
   quand il revient à 0 (`fermer`). Les appels sont idempotents.
3. Un réglage `KEEP_AWAKE_DURING_RUNS` (défaut `true`) permet de le
   désactiver, documenté dans `docs/configuration.md` et `.env.example`.
4. Au shutdown du backend (lifespan), `relacher()`.

## Critères d'acceptation

- [ ] Un test de `backend/tests/test_eveil.py` vérifie que l'ouverture du premier run appelle `retenir()` une fois, et qu'un second run ouvert ne le rappelle pas
- [ ] Un test de `backend/tests/test_eveil.py` vérifie que `relacher()` n'est appelé qu'à la fermeture du dernier run ouvert
- [ ] Un test de `backend/tests/test_eveil.py` vérifie qu'avec `keep_awake_during_runs` à faux, ni `retenir()` ni `relacher()` n'appellent l'API système
- [ ] Un test de `backend/tests/test_eveil.py` vérifie qu'une exception levée par l'appel système est journalisée sans être propagée
- [ ] Un test de `backend/tests/test_eveil.py` vérifie que les drapeaux passés à `SetThreadExecutionState` sont `ES_CONTINUOUS | ES_SYSTEM_REQUIRED` pour `retenir()` et `ES_CONTINUOUS` pour `relacher()` (API système simulée)

## Dépendances

Aucune.

## Estimation

0,5 jour.

## Risques

`SetThreadExecutionState` s'applique au thread appelant : il doit être appelé
depuis le thread de la boucle asyncio, qui vit autant que le backend. Une
veille forcée (capot fermé, menu « Mettre en veille ») n'est pas empêchée :
c'est voulu.

## Ce que ça ne fait pas

- N'empêche pas un redémarrage de Windows Update.
- N'empêche pas l'extinction de l'écran.
