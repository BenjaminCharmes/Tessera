---
agent: codeur
created: 2026-11-03
depends_on: []
estimated_days: 1
id: ticket-762
pr_number: 867
priority: high
status: done
title: A declared service started by hand shows as running in its server room
type: fix
---

# ticket-762 — Un service déclaré lancé à la main s'affiche en marche dans sa salle serveur

## Objectif

La baie d'un service qui tourne, lancé hors de l'IDE, dit qu'il tourne.

## Contexte

Audit du 30/10 (relecture du 03/11), ticket-710. `GET /projects/{id}/services` rend aussi les
services déclarés non lancés (`pid: null`, `backend/src/tessera/routers/services.py`).
L'inventaire nomme l'app externe du nom du service. `baiesDuProjet`
(`frontend/src/components/EnCoursView/baies.ts`) prend l'état du service déclaré
(`jamais-lance`) et saute l'app réelle parce que le nom est déjà pris. Vérifié : une app
externe `api` et un service `api` sans pid donnent `jamais-lance`, « pas lancé par l'IDE ».
Cas réel : Vigie lancé à la main sur 8025 affiche sa baie éteinte et sa ventilation à l'arrêt.

## Critères d'acceptation

- [ ] Un test vérifie que `baiesDuProjet([app externe "api"], [service "api", pid null])` rend
      l'état `en-cours` avec le libellé « lancé à la main »
- [ ] Un test vérifie qu'un service déclaré sans app correspondante reste `jamais-lance`
- [ ] Un test vérifie qu'un service lancé par l'IDE garde son état et son libellé