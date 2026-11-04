---
agent: codeur
created: 2026-11-03
depends_on: []
estimated_days: 1
id: ticket-754
pr_number: null
priority: medium
status: done
title: The observation socket trusts only declared origins, not every loopback port
type: fix
---

# ticket-754 — La socket d'observation ne fait confiance qu'aux origines déclarées

## Objectif

Une page servie en local par une app qu'un agent a écrite ne peut pas observer les runs ni
répondre à un agent à la place de l'utilisateur.

## Contexte

Audit du 30/10 (relecture du 03/11), ticket-704. `_is_allowed_origin('http://localhost:61234')`
rend vrai (vérifié) : toute origine loopback, sur tout port, est admise. Or Tessera sert sur
le loopback des apps écrites par ses agents (`services`, `pipeline.controle_visuel`).
CORS ne couvre pas la WebSocket : une telle page peut ouvrir `WS /orchestrator/observe`,
lire tous les runs et envoyer `{"genre":"answer"}` (`backend/src/tessera/routers/observation.py`).
Les POST JSON restent bloqués par le préflight CORS (seul `localhost:5173` est admis).

## Solution proposée

Un réglage `ALLOWED_ORIGINS` (défaut : `http://localhost:5173` à `5176`, leurs équivalents
`127.0.0.1`, et l'origine Tauri) : le contrôle d'`Origin` des WebSocket ne compare qu'à
cette liste. Le contrôle de `Host` ne change pas.

## Critères d'acceptation

- [ ] Un test vérifie qu'un `Origin: http://localhost:61234` sur `/orchestrator/observe` est
      refusé (fermeture 4403)
- [ ] Un test vérifie que `Origin: http://localhost:5173` et l'origine Tauri sont admis
- [ ] Un test vérifie qu'une origine ajoutée par `ALLOWED_ORIGINS` est admise
- [ ] `docs/configuration.md` décrit `ALLOWED_ORIGINS` et son défaut