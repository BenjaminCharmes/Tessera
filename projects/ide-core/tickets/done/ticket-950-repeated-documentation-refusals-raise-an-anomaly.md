---
agent: codeur
created: 2026-11-12
depends_on: []
estimated_days: 0.5
id: ticket-950
pr_number: null
priority: high
status: done
title: Documentation refused on several runs in a row raises an anomaly
type: fix
---

# ticket-950 — Une documentation refusée plusieurs runs de suite lève une anomalie

## Objectif

Qu'un échec qui se répète d'un run à l'autre sans bloquer les runs se voie en
quelques runs, pas en trois semaines.

## Contexte

La documentation de Curio a été refusée à chaque run approuvé, du ticket-036
au ticket-096, sans que personne ne le voie (corrigé par le ticket-940). Les
runs, eux, étaient approuvés et livrés : aucune règle du détecteur
d'anomalies (ADR-078) ne regarde au-delà du ticket en cours.
`blocages_identiques` ne compare que les deux derniers runs d'un même ticket.

Les données existent déjà : chaque lot de documentation émet un événement
`doc_updated`, stocké dans `agent_events` avec `fichiers` et `refus`.

## Solution proposée

1. `lecture_historique` gagne une lecture des `N` derniers événements
   `doc_updated` d'un projet (jointure sur `pipeline_runs.project_id`), du plus
   récent au plus ancien.
2. Une règle `documentation_refusee_en_serie` (`regles_historiques.py`) :
   quand les **3** derniers lots du projet ont tous au moins un refus et
   aucun fichier modifié, elle rend une `Anomalie` dont la clé tient au lot le
   plus récent (un épisode, pas une règle), avec un message en français sans
   recopier le motif.
3. Le détecteur l'évalue avec les autres règles historiques, pour le projet
   du run actif, et la signale par le même chemin (`run_anomaly`).

## Critères d'acceptation

- [ ] Un test : trois lots refusés sans fichier → une anomalie
      `documentation_refusee_en_serie`, mesure 3, seuil 3.
- [ ] Un test : deux lots refusés puis un lot qui modifie un fichier → pas
      d'anomalie.
- [ ] Un test : moins de trois lots → pas d'anomalie.
- [ ] Un test, sur une base SQLite temporaire : la lecture ne rend que les
      `doc_updated` du projet demandé, du plus récent au plus ancien.
- [ ] Un test : le message de l'anomalie ne contient pas le texte d'un
      motif de refus.
- [ ] `Regle` (`anomalies/modeles.py`) accepte la nouvelle valeur, et le
      frontend qui affiche les anomalies la libelle (test vitest).

## Ce que ça ne fait pas

- Ne corrige rien : le détecteur observe sans gouverner (ADR-078).
- Ne surveille pas les autres échecs répétés (CI rouge, services) : une
  règle par cas, quand il se présente.
## Livraison

Run bloqué au 3e tour par un seul test, sans lien avec le diff :
`test_usage_stats_responds_in_under_two_seconds_on_fifty_thousand_rows`
(6,5 s puis 5,8 s pour un seuil de 2 s, pendant que quatre files tournaient en
parallèle). Vérifié à la main par la session ide-core le 12/11 : les tests des
anomalies et `test_usage_stats.py` passent seuls (115), mypy, ruff, vitest,
tsc et eslint aussi.
