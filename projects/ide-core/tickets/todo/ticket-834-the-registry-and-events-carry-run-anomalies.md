---
id: ticket-834
title: "The run registry, the event stream and the settings carry run anomalies"
type: feat
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-11-05
---

# ticket-834 — Le registre, le flux d'événements et les réglages portent les anomalies

## Objectif

Poser le socle du détecteur d'anomalies (ADR-078) : l'endroit où une anomalie vit, son modèle,
son événement et ses réglages. Aucune règle ni tâche de fond ici.

## Contexte

Conception : `docs/superpowers/specs/2026-11-05-detecteur-d-anomalies-design.md`, sections « Les
contrats » et « Une seule fois ». Une anomalie vit dans `RunActif`, comme `question` (ticket-163) :
un client qui se connecte après coup la voit, et elle meurt avec le run.

## Solution

- `RunActif` (`services/run_registry.py`) gagne `dernier_evenement_a: datetime | None`,
  `attente_exterieure: bool`, `anomalies: list[dict]` (20 au plus, la plus ancienne sort) et
  `anomalies_vues: set[str]`. `anomalies` entre dans `en_dict()` ; `anomalies_vues` **n'y entre
  pas**.
- `RunRegistry.vivants() -> list[RunActif]`.
- `_suivre` (`services/run_executor.py`) pose `dernier_evenement_a` à **chaque** événement,
  tokens et appels d'outils compris, et `attente_exterieure` sur `external_wait` (`waiting`).
- `EventType.RUN_ANOMALY = "run_anomaly"` (`services/pipeline_events.py`), absent de `JETABLES`.
- `services/anomalies/modeles.py` : `Anomalie` (champs de la spec), `message` borné à 200
  caractères.
- `config.py` : `anomalies_actives = True`, `anomalie_intervalle_s = 300.0`,
  `anomalie_outil_repete = 4`, `anomalie_silence_s = 900.0`, `anomalie_tours = 3`,
  `anomalie_facteur_median = 3.0`, `anomalie_echantillon_min = 10`, `anomalie_fenetre = 20`,
  `anomalie_plancher_etape_s = 300.0`, `anomalie_plancher_cout_usd = 0.5`,
  `anomalie_part_budget = 0.8`.
- Si un test de contrat (ticket-765) couvre `RunActif` ou les types d'événement, il est mis à jour.

## Critères d'acceptation

- [ ] `test_en_dict_exposes_anomalies_and_hides_the_seen_keys` : `anomalies` est dans `en_dict()`,
      `anomalies_vues` n'y est pas
- [ ] `test_suivre_sets_last_event_time_on_every_event_type` : un token, un appel d'outil et un
      `ticket_status_changed` posent tous `dernier_evenement_a`
- [ ] `test_suivre_tracks_external_wait` : `waiting: true` pose `attente_exterieure`, `waiting:
      false` la retire
- [ ] `test_registry_vivants_lists_open_runs_only` : un run fermé en est absent
- [ ] `test_run_anomaly_is_not_droppable` : `RUN_ANOMALY` n'est pas dans `JETABLES`, et une file
      saturée de tokens l'accepte
- [ ] `test_anomalie_message_at_200_chars_is_kept` et `test_anomalie_message_at_201_chars_is_refused`
- [ ] `test_anomalies_list_keeps_the_20_most_recent` : 20 anomalies sont gardées, la 21e fait
      sortir la plus ancienne
- [ ] `test_anomaly_settings_defaults` : les valeurs par défaut sont celles de la spec

## Ce que ça ne fait pas

Aucune règle, aucune lecture SQL, aucune tâche de fond, aucun affichage.
