---
id: ticket-201
title: "L'onglet Coûts devient un tableau de statistiques avec graphiques"
type: feat
status: in-review
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 2
created: 2026-09-28
---

# ticket-201 — L'onglet Coûts devient un tableau de statistiques avec graphiques

## Objectif

Que l'utilisateur lise d'un coup d'œil **quand** il dépense, **à quel point**
les runs aboutissent et **en combien de temps**, pas seulement où part l'argent.

## Contexte

`CostView` ventile la dépense par agent, modèle et projet, sans aucune
dimension de temps : impossible de voir une tendance, un pic, ou un taux
d'approbation qui baisse. Les données existent déjà — `agent_calls` porte
`created_at`, tokens, `cost_usd`, `duration_ms`, `role`, `model` ;
`pipeline_runs` porte `approved`, `final_status`, `rounds` — mais aucun
endpoint n'accepte de période ni ne rend de série.

Aucune librairie de graphiques n'est installée, et ADR-026 ne prévoit pas de
couleurs pour des séries de données.

## Solution proposée

**Backend** — un endpoint `GET /api/v1/usage/stats?days=7|30|90&project_id=`
(projet optionnel : absent = tous projets) qui rend en une réponse :

- KPI de la période : runs, appels, tokens entrants / sortants / cache,
  coût total, dont chat (`chat_messages.cost_usd`), durée cumulée des appels ;
- série quotidienne complète (un point par jour, jours vides à zéro) :
  runs, tokens entrants, tokens sortants, coût ;
- ventilations par agent, par modèle, par projet (ce dernier en vue globale) ;
- qualité : taux d'approbation, répartition des `final_status`, rounds moyens ;
- durées : durée moyenne d'un run, durée moyenne d'un appel par agent ;
- les 10 runs les plus récents de la période.

Regroupement par jour **UTC** — c'est ainsi que les horodatages sont stockés.
Le projet d'un appel passe par la jointure `agent_calls.run_id → pipeline_runs`.

**Frontend** — l'entrée « Coûts » du rail devient « Statistiques » ; `CostView`
est remplacée par le tableau (sélecteur 7/30/90 jours, KPI, graphiques,
tableau des runs). Graphiques en SVG maison dans `design/charts/` : série
temporelle, anneau, barres horizontales. Pas de dépendance ajoutée.

**Palette** — un ADR dédie aux graphiques une palette de données, utilisable
seulement depuis `design/charts/` ; `coherence.test.ts` le vérifie. Les barres
ambre de `UsageDashboard` (ambre = attente) passent sur cette palette.

## Critères d'acceptation

- [x] `GET /api/v1/usage/stats?days=30` renvoie 200 avec une série de 30 points exactement, jours sans activité à zéro
- [x] Avec `project_id`, KPI, série et ventilations ne comptent que les runs de ce projet
- [x] Sur une base vide, l'endpoint renvoie 200 avec des totaux à zéro et `approval_rate` à `null`
- [x] Un appel hors de la période n'est compté nulle part
- [x] `days` hors de {7, 30, 90} est refusé en 422
- [x] L'entrée du rail s'intitule « Statistiques » et affiche le tableau au centre
- [x] Le tableau affiche un état vide explicite quand la période ne contient aucun run
- [x] Un test de composant couvre chaque graphique de `design/charts/` (rendu vide et rendu avec données)
- [x] `coherence.test.ts` échoue si une couleur de la palette de données est utilisée hors de `design/charts/`
- [x] Un ADR décrit la palette de données, dans le budget de `write-adr`
- [x] `uv run pytest`, `npm run test` et `npm run build` passent

## Ce que ça ne fait pas

- Pas d'export, pas de plage de dates libre, pas de filtre par agent
- Pas d'historique du quota : il n'est pas persisté
- Pas de fuseau local : les jours sont des jours UTC, et l'écran le dit
- Le chat n'entre que dans la dépense totale : il n'a ni tokens ni modèle en base

## Dépendances

Aucune.

## Estimation

2 jours.

## Risques

- Un seul endpoint gros : garder la requête découpée en fonctions (<200 lignes par fichier)
- `/usage/stats` à la racine plutôt que sous `/projects` : vérifier qu'aucune route `/projects/{id}` ne le capture
