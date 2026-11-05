---
id: ticket-839
title: "A background task watches live runs and reports each anomaly once"
type: feat
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: [ticket-838]
estimated_days: 1
created: 2026-11-05
---

# ticket-839 — Une tâche de fond observe les runs vivants et signale chaque anomalie une fois

## Objectif

Brancher les six règles (tickets 795 à 798) sur les runs vivants : une passe toutes les 5 minutes,
en lecture seule, un signalement par épisode (ADR-078).

## Contexte

Spec `docs/superpowers/specs/2026-11-05-detecteur-d-anomalies-design.md`, sections « Où il
tourne », « Une seule fois » et « Ce qu'il ne fait jamais ». Règle en vigueur proposée dans
`contraintes.md` : le détecteur observe, il ne gouverne pas. Un backend local n'a qu'un process
(ADR-038) : une tâche asyncio suffit.

## Solution

- `services/anomalies/detecteur.py` : `DetecteurDAnomalies(registre, hub, db_path, reglages)`,
  `passe() -> list[Anomalie]` et `boucle()`.
- Une passe parcourt `RunRegistry.vivants()`. Pour chaque run, elle lit (ticket courant), applique
  les règles, écarte les clés déjà dans `anomalies_vues`, puis **émet** chaque nouvelle anomalie :
  événement `run_anomaly` par l'`emetteur` du run (publication puis persistance dans
  `agent_events`), ajout à `RunActif.anomalies`, clé dans `anomalies_vues` **après** l'émission,
  ligne `anomalie_de_run` dans le log (règle, ticket, mesure, seuil ; jamais l'`input` d'un outil).
- La passe ne mute rien d'autre que `anomalies` et `anomalies_vues`. Elle n'appelle ni provider,
  ni `git`, ni `gh`, et n'écrit pas `pipeline-log.md`.
- `silence` reçoit `exempte` si une question attend ou si `attente_exterieure` est vrai, ou si
  l'étape ouverte est silencieuse (`tests`, `securite`, `validation`, `documentation`,
  `livraison`) **et** que sa médiane est armée (10 échantillons).
- `cout_budget` n'est évalué que pour un run `autonomous`.
- Une exception sur un run se journalise (`anomalie_passe_en_echec`) et la passe continue sur les
  autres. Une passe qui démarre plus de deux fois l'intervalle après la précédente journalise
  `anomalie_passe_tardive` avec l'écart, et émet quand même.
- `main.py` : dans le `lifespan`, après `_reprendre_les_surveillances()`, une tâche `boucle()`
  créée si `anomalies_actives`, annulée puis attendue à l'arrêt.
- Dans une file, les événements du run sont ceux de l'enveloppe, filtrés par `ticket_id` : le
  signalement porte donc le `ticket_id` du ticket courant.

## Critères d'acceptation

- [ ] `test_passe_without_live_runs_returns_nothing`
- [ ] `test_passe_reports_each_rule_once_per_episode` : une double passe sur le même état, pour
      chacune des six règles, n'émet qu'un événement
- [ ] `test_passe_reports_again_after_the_series_breaks_and_reforms` : une série d'outils rompue
      puis reformée, et un silence rompu puis repris, donnent une seconde clé
- [ ] `test_passe_marks_the_key_seen_only_after_the_emission`
- [ ] `test_passe_emits_through_the_hub_and_persists_in_agent_events`
- [ ] `test_passe_on_a_queue_persists_under_the_envelope_with_the_ticket_id`
- [ ] `test_passe_never_changes_a_run_beyond_its_anomaly_fields` : les autres champs du `RunActif`
      sont identiques avant et après ; aucun `fermer`, aucun appel au dialogue
- [ ] `test_passe_calls_no_provider_and_runs_no_git_command`
- [ ] `test_passe_survives_a_failing_run_and_still_checks_the_others`
- [ ] `test_silence_is_exempt_during_a_silent_stage_with_an_armed_median` et
      `test_silence_is_reported_during_a_silent_stage_without_a_median`
- [ ] `test_silence_is_exempt_while_a_question_waits_and_during_an_external_wait`
- [ ] `test_cout_budget_is_evaluated_only_for_an_autonomous_run`
- [ ] `test_passe_late_by_601s_logs_the_gap_and_late_by_600s_does_not` (intervalle 300 s)
- [ ] `test_boucle_does_nothing_when_anomalies_actives_is_false`
- [ ] `test_lifespan_starts_the_detector_and_cancels_it_on_shutdown`
- [ ] `test_anomaly_log_line_has_no_tool_input`

## Ce que ça ne fait pas

Aucun affichage (tickets 800 à 833). Ne coupe, ne relance, ne suspend rien. N'écrit aucune table :
l'historique est `agent_events`.
