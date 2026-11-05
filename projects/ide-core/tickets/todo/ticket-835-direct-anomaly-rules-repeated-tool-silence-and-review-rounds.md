---
id: ticket-835
title: "Direct anomaly rules: repeated tool, silence and review rounds"
type: feat
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: [ticket-834]
estimated_days: 1
created: 2026-11-05
---

# ticket-835 — Règles directes : outil répété, silence, tours de revue

## Objectif

Trois règles du détecteur (ADR-078) qui se jugent sur l'état du run, sans historique : une série
d'appels d'outil identiques, un silence de 15 minutes, le dernier tour de revue.

## Contexte

Spec `docs/superpowers/specs/2026-11-05-detecteur-d-anomalies-design.md`, section « Les règles ».
Le 03/11, trois tours ont été perdus sur des doubles de test ; l'indicateur « figé ? » du
navigateur ne voit pas une étape silencieuse. Les règles sont **pures** : l'instant est un
paramètre, aucune I/O.

## Solution

- `services/anomalies/regles_directes.py` : `outil_repete`, `silence`, `tours_de_revue`, avec les
  signatures de la spec. Seuils lus de `settings` (ticket-834) par l'appelant, passés en
  paramètres.
- `outil_repete` : série d'**au moins 4** appels consécutifs, même agent, même `tool`, même
  `input_hash`. La clé est l'`id` du premier appel de la série. Le message nomme l'outil, jamais
  son `input`.
- `silence` : `maintenant - dernier >= seuil_s`, sauf `exempte` (question en attente, attente
  extérieure) ou `dernier` absent.
- `tours_de_revue` : `tour >= 3` ; la clé est `tours:<ticket>`, donc une fois par ticket et par run.
- `services/anomalies/lecture_evenements.py` : `AppelOutil` (`id`, `agent`, `tool`, `input_hash`
  — le hachage du JSON canonique, clés triées) et `derniers_appels_d_outils(db_path, run_id,
  ticket_id, n=8)`, lecture seule des `agent_tool_use` du ticket posés **après** le dernier
  `agent_started`.

## Critères d'acceptation

- [ ] `test_outil_repete_three_identical_calls_is_none` et
      `test_outil_repete_four_identical_calls_reports` (3 sous le seuil, 4 au seuil)
- [ ] `test_outil_repete_five_calls_keeps_the_key_of_the_series_start` : 5 appels donnent la clé
      des 4
- [ ] `test_outil_repete_a_different_input_or_tool_in_between_breaks_the_series`
- [ ] `test_outil_repete_message_never_contains_the_tool_input` : un `input` portant un faux
      jeton ne se retrouve pas dans `message`
- [ ] `test_silence_899s_is_none` et `test_silence_900s_reports`
- [ ] `test_silence_is_none_when_exempt_or_when_no_event_was_seen`
- [ ] `test_tours_de_revue_round_2_is_none` et `test_tours_de_revue_round_3_reports`
- [ ] `test_derniers_appels_d_outils_ignores_calls_before_the_last_agent_started`
- [ ] `test_derniers_appels_d_outils_never_writes` : la base est ouverte en lecture seule ou
      inchangée après l'appel
- [ ] `test_input_hash_is_stable_across_key_order`

## Ce que ça ne fait pas

Pas de boucle, pas d'émission, pas de dédoublonnage : c'est le ticket-839. Les règles à
historique sont les tickets 796 à 798.
