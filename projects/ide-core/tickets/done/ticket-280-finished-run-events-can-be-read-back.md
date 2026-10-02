---
agent: codeur
created: 2026-10-01
depends_on: []
estimated_days: 1
id: ticket-280
plan: true
pr_number: 173
priority: medium
status: done
title: A finished run's events can be read back through the API
type: feat
---

# ticket-280 — Les événements d'un run terminé se relisent

## Objectif

Que l'API rende la suite d'événements d'un run terminé, pour que le frontend
puisse rouvrir sa vue (ticket-281) sans rien relancer.

## Contexte

Tout est déjà écrit : `emetteur` persiste chaque événement dans la table
`agent_events` (`services/run_executor.py:56-75`, `database.py:256-269`). Rien
ne le relit : `agent_events` n'a que des `INSERT`, et le seul endpoint
d'historique, `GET /projects/{id}/runs`, ne rend que des résumés.

Deux identifiants coexistent : le `run_id` du registre, celui que voit la
WebSocket (ADR-041), et l'identifiant en base créé par `create_run`
(`run_id_en_base`). Les événements sont rangés sous le second. Pour une file
ou un run autonome, `run_id_en_base` est la ligne enveloppe ; les lignes par
ticket viennent de `_run_recorder` (`services/orchestrator.py:197-205`).

## Solution proposée

- `GET /api/v1/runs/{run_id}/events` rend les événements du run, dans l'ordre
  d'émission, au format des événements de la WebSocket. 404 si le run est
  inconnu.
- Les `agent_token` sont exclus de la réponse, filtrés en SQL : la vue relue
  n'a besoin que du texte final, déjà dans `agent_done`.
- `run_closed` et le résumé de `GET /projects/{id}/runs` portent l'identifiant
  qui permet d'appeler cet endpoint.
- Le tour de plan tranche le cas des lignes par ticket d'une file : soit elles
  renvoient à leur enveloppe, soit l'endpoint filtre sur `ticket_id`.

## Critères d'acceptation

- [ ] Un test vérifie que `GET /api/v1/runs/{id}/events` rend les événements
      enregistrés pour ce run, dans l'ordre de leur `ts`
- [ ] Un test vérifie qu'aucun événement `agent_token` n'est rendu
- [ ] Un test vérifie le 404 sur un identifiant inconnu
- [ ] Un test vérifie que l'événement `run_closed` porte l'identifiant en base
      du run
- [ ] Un test vérifie qu'un ticket joué dans une file, tel que rendu par
      `GET /projects/{id}/runs`, permet d'obtenir ses propres événements

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

`agent_events` contient aussi les tokens, donc la table peut être lourde :
d'où le filtre en SQL plutôt qu'en Python.