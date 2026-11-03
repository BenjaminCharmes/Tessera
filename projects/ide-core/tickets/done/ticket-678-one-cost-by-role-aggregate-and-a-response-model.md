---
agent: codeur
created: 2026-10-29
depends_on: []
id: ticket-678
pr_number: 800
priority: medium
status: done
title: One cost-by-role aggregate and a response model
type: refactor
---

# ticket-678 — Un agrégat de coût par rôle, un modèle de réponse

## Objectif
Le coût par rôle ne s'agrège qu'une fois, et `GET …/usage/breakdown` rend un
modèle Pydantic.

## Contexte
`services/database.py:656` (`get_usage_breakdown`, rendu en `dict`) et
`services/usage_stats.py:82` (`_breakdown(…, "ac.role")`, rendu en
`UsageStats`) agrègent la même chose par deux requêtes
(`docs/audit/doublons.md` §1.4). Les deux routes de `routers/projects.py:715-724`
n'ont pas de `response_model`. Le front type à la main
(`lib/ventilation.ts:5-15`).

## Critères d'acceptation
- [ ] Une seule requête SQL agrège le coût par rôle ; `get_usage_breakdown` ou `usage_stats` l'appelle, pas les deux avec leur copie
- [ ] Les deux routes `usage/breakdown` déclarent un `response_model` ; le schéma OpenAPI les décrit
- [ ] Sur une même base de test, la somme `per_agent` de `get_usage_breakdown` égale celle de `usage_stats` sur la même fenêtre (test)
- [ ] Les tests existants de `database` et `usage_stats` passent sans modification de leurs attendus

## Ce que ça ne fait pas
- Ne change aucun champ de la réponse existante : le front actuel continue de la lire
- Ne modifie pas le type front (ticket-684)