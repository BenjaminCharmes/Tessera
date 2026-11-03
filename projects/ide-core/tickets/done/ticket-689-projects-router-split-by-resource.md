---
agent: codeur
created: 2026-10-29
depends_on:
- ticket-678
- ticket-679
id: ticket-689
pr_number: 811
priority: low
status: done
title: Projects router split by resource
type: refactor
---

# ticket-689 — `routers/projects.py` découpé par ressource

## Objectif
Un routeur par ressource, les chemins et les réponses inchangés.

## Contexte
`routers/projects.py` (826 lignes) enregistre huit ressources : projets et
import/clone, git, mode d'artefacts, agents, réglages du pipeline, usage,
nettoyage, retrait (`docs/audit/refactos.md` §1). Les handlers sont courts (le
plus long : 52 lignes). Les tickets 678 et 679 déplacent les routes d'usage :
découper avant produirait un conflit.

## Critères d'acceptation
- [ ] Aucun routeur issu du découpage ne dépasse 300 lignes ; l'entrée de `routers/projects.py` disparaît de `PLAFONDS` ou y est baissée sous 300 en le retirant
- [ ] Les couples (méthode, chemin) de `app.openapi()["paths"]` sont identiques avant et après ; un test les fige, écrit avant le déplacement
- [ ] Si une route à chemin fixe (`/usage/breakdown`) cohabite avec `/{project_id}`, l'ordre d'enregistrement qui la fait passer avant est conservé ; un test appelle chaque chemin fixe et obtient sa réponse, pas un 404 de projet
- [ ] `uv run pytest` et `uv run mypy` passent ; aucun test d'endpoint ne change d'attendu

## Ce que ça ne fait pas
- Ne retype aucune réponse (tickets 678, 679, 684)
- Ne découpe pas `routers/tickets.py` ni `routers/chat.py` : à faire quand ce patron aura servi