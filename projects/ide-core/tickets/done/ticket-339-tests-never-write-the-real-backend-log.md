---
id: ticket-339
title: "The test suite never writes the real backend log"
type: test
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 0.25
created: 2026-10-05
---

# ticket-339 — La suite de tests n'écrit plus dans le vrai journal du backend

## Objectif

Que `backend/logs/tessera.log` ne contienne que ce que le backend a vraiment
fait, pour que la trace d'un plantage y reste (ticket-330).

## Contexte

Constaté le 2026-10-05 en cherchant pourquoi le résolveur de conflits
n'avait pas tranché un conflit de démineur : le journal réel contenait des
dizaines d'entrées venues des tests (`jamais-vu.py`, `app.py`), répétées à
l'identique. Chaque `TestClient(app)` exécute le `lifespan`, qui ajoute au
logger racine un `RotatingFileHandler` sur le fichier réel, jamais retiré :
après N démarrages, chaque ligne s'y écrit N fois. Les fichiers de 10 Mo
tournent, et la trace d'un vrai plantage peut disparaître sous ce bruit.

## Solution proposée

Une fixture de session dans `conftest.py` remplace `configure_file_logging`
de `tessera.main` par un no-op pendant les tests. La fonction reste testée
directement dans `test_logger.py`.

## Critères d'acceptation

- [x] Un test démarre l'application deux fois par `TestClient` et vérifie
      qu'aucun gestionnaire du logger racine n'écrit dans
      `settings.ide_log_file`

## Ce que ça ne fait pas

Le gestionnaire ajouté par chaque démarrage n'est toujours pas retiré à
l'arrêt : en production, l'application ne démarre qu'une fois par processus.

## Dépendances

Aucune.

## Estimation

0,25 jour.
