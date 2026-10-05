---
id: ticket-335
title: "The recent runs card can show more runs and search them by ticket or project"
type: feat
status: done
pr_number: 252
priority: low
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-05
---

# ticket-335 — Les runs récents s'étendent et se cherchent

## Objectif

Retrouver un run plus ancien que les dix derniers de la vue Statistiques.

## Contexte

Retour de l'utilisateur le 2026-10-05 : « Runs récents » n'affiche que les
dix derniers (`RECENT_RUNS_LIMIT`), sans moyen d'en voir plus ni de
chercher. Ces dix lignes viennent de `/usage/stats`, qui calcule tout
l'écran : l'agrandir pour en montrer plus recalculerait tout.

## Solution proposée

- `GET /usage/recent-runs?days&project_id&limit&q` : les derniers runs de
  tickets de la période (sans les enveloppes de file), `limit` entre 1 et
  200, `q` cherché dans l'id du ticket ou du projet, `%` et `_` pris à la
  lettre.
- La carte ajoute une recherche (lancée quand la frappe s'arrête) et
  « Afficher plus » (+20). Sans interaction, elle garde les dix runs venus
  avec les statistiques, sans requête de plus.

Pas de tri : la liste est chronologique, et le tri par coût ou durée a déjà
ses graphiques.

## Critères d'acceptation

- [x] Un test vérifie que `recent_runs` rend jusqu'à `limit` runs, du plus
      récent au plus ancien
- [x] Un test vérifie que la recherche trouve un ticket ou un projet, sans
      enveloppe de file, et que `%` et `_` ne sont pas des jokers
- [x] Un test vérifie que l'endpoint transmet `limit` et `q` et refuse
      `limit` au-delà de 200
- [x] Un test vérifie que la carte n'appelle pas l'API sans interaction, que
      « Afficher plus » demande trente runs, que la recherche ne part qu'une
      fois la frappe finie, et qu'une recherche vide le dit

## Dépendances

Aucune.

## Estimation

0,5 jour.
