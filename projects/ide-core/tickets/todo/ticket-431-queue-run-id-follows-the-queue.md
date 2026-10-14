---
id: ticket-431
title: "The run id returned when launching a queue can be followed: its events, its current ticket and the tickets left"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-10-14
plan: true
---

# ticket-431 — Suivre une file par l'id que l'API vient de rendre

## Objectif

Qu'une session (ou l'IDE) qui lance une file puisse la suivre avec l'id
qu'elle a reçu, et savoir où elle en est.

## Contexte

Signalement d'affût, 2026-10-14 (récupéré, voir ticket-430) :
`POST /api/v1/orchestrator/run` en mode `queue` (13 tickets) renvoie
`run_id` 92571cf0… ; `GET /api/v1/runs/92571cf0…/events` répond 404
« Run inconnu ». Les runs de `GET /api/v1/projects/affut/runs` portent
d'autres ids (un parent, des enfants par ticket). Aucun endpoint ne dit où
en est une file : ticket courant, tickets faits, tickets restants.
Contournement de la session : poller `/projects/affut/runs` et filtrer.

La charge utile de `POST /orchestrator/run` n'est par ailleurs documentée
nulle part côté projet (vigie a dû lire `routers/orchestrator.py`).

## Solution proposée

- Établir au tour de plan le lien entre l'id rendu par `RUN_REGISTRY`
  (`routers/orchestrator.py`) et les lignes de `pipeline_runs` (parent,
  enfants).
- `GET /api/v1/runs/{run_id}/events` accepte l'id rendu au lancement et
  renvoie les évènements de toute la file.
- `GET /api/v1/runs/{run_id}` : `{ project_id, mode, statut (en cours |
  terminé | interrompu), ticket_courant, faits: [...], restants: [...],
  debut, fin }`, pour un run vivant comme terminé.
- `docs/api.md` documente `POST /orchestrator/run` (champs, modes, exemple
  de file) et le nouvel endpoint.

## Critères d'acceptation

- [ ] Un test vérifie que `GET /runs/{id}/events` avec l'id rendu par un
      lancement en mode `queue` ne renvoie pas 404
- [ ] Un test vérifie que `GET /runs/{id}` d'une file en cours donne le ticket
      courant, les faits et les restants
- [ ] Un test vérifie que `GET /runs/{id}` d'une file terminée donne
      `statut: "terminé"` et ses tickets faits
- [ ] `docs/api.md` décrit la charge utile de `POST /orchestrator/run` avec
      un exemple en mode `queue`

## Dépendances

Aucune.
