---
id: ticket-690
title: "Database module split by domain"
type: refactor
status: todo
priority: low
agent: codeur
depends_on: [ticket-678]
created: 2026-10-29
---

# ticket-690 — `database.py` découpé par domaine

## Objectif
Un module par domaine de données, aucun au-dessus du plafond général.

## Contexte
`services/database.py` (691 lignes) : schéma (`init_db`, 106-145), runs
(`create_run` à `list_runs_for_ticket`), événements, usage, messages de chat,
conversations (`docs/audit/refactos.md` §1). Le ticket-678 réécrit
`get_usage_breakdown` : découper avant le ferait deux fois.

## Critères d'acceptation
- [ ] Aucun module issu du découpage ne dépasse 300 lignes ; l'entrée de `services/database.py` disparaît de `PLAFONDS`
- [ ] Le schéma SQL et ses migrations restent dans un seul module ; `version_du_schema` s'y trouve
- [ ] Chaque importeur est mis à jour : `grep -rn "services.database import" backend/src backend/tests` ne rend que des noms qui existent (mypy le vérifie)
- [ ] Les tests qui patchent un nom de `database` sont listés dans la PR et réécrits sans changement d'attendus
- [ ] `uv run pytest` et `uv run mypy` passent

## Ce que ça ne fait pas
- Ne change aucune requête ni aucun schéma
- Ne fusionne pas `get_usage_breakdown` avec `usage_stats.py` (ticket-678)
