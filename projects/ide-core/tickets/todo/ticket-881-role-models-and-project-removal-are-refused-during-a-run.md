---
agent: codeur
created: 2026-11-06
depends_on: ["ticket-880"]
estimated_days: 0.5
id: ticket-881
pr_number: null
priority: high
status: todo
title: A role's model cannot be changed and a project cannot be removed while any run is live
type: feat
---

# ticket-881 — Modèle d'un rôle et retrait de projet refusés pendant un run

## Objectif

Pendant qu'un run vit, aucune requête ne peut remplacer le modèle ou le
provider d'un rôle d'un projet, ni retirer ou détacher un projet.

## Contexte

Le ticket-880 a posé `refuser_pendant_un_run` sur `PATCH …/pipeline` et sur
`backend/src/tessera/routers/agent_admin.py`. Deux routes de la même classe
sont restées ouvertes :

- `PUT /api/v1/projects/{id}/agents/{role}`
  (`backend/src/tessera/routers/projects/agents.py`) change le modèle, le
  provider et le repli d'un rôle. Passer l'audit `securite` ou le `reviewer`
  sur un modèle faible ou local abaisse une porte : sur ide-core, un modèle
  local rejoué sur une faille réelle ne la voyait pas.
- `DELETE /api/v1/projects/{id}` et `POST /api/v1/projects/{id}/detach`
  (`backend/src/tessera/routers/projects/removal.py`) retirent un projet.

## Solution proposée

Réutiliser `refuser_pendant_un_run` (ticket-880) comme dépendance sur ces
trois routes : 409 tant qu'un run est vivant sur n'importe quel projet. Un
changement de modèle accepté s'écrit en `warning` `porte_abaissee` avec le
projet, le rôle et le modèle.

## Critères d'acceptation

- [ ] Un test de `backend/tests/test_portes_voisines.py` vérifie qu'avec un
      run vivant sur un autre projet, `PUT /api/v1/projects/<id>/agents/securite`
      rend 409.
- [ ] Un test vérifie qu'avec un run vivant, `DELETE /api/v1/projects/<id>`
      et `POST /api/v1/projects/<id>/detach` rendent 409.
- [ ] Un test vérifie que sans run vivant, `PUT …/agents/<role>` rend 200 et
      journalise `porte_abaissee`.
- [ ] Le diff ajoute la dépendance dans
      `backend/src/tessera/routers/projects/agents.py` et
      `backend/src/tessera/routers/projects/removal.py`.

## Dépendances

ticket-880 (`refuser_pendant_un_run`).

## Estimation

Une demi-journée.

## Risques

Benjamin ne change plus le modèle d'un rôle pendant une file : il attend sa
fin. C'est voulu.
