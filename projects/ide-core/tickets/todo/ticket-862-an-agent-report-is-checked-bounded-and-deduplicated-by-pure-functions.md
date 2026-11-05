---
id: ticket-862
title: "An agent report is checked, bounded and deduplicated by pure functions"
type: feat
status: todo
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-11-05
pr_number: null
---

# ticket-862 — Un signalement d'agent : contrôle, bornes, doublons

## Objectif

`services/providers/signal_agent.py` : tout ce qui décide si un appel de `signaler` est reçu,
sans l'outil lui-même.

## Contexte

ADR-080, spec §3. Un agent qui rencontre un défaut de Tessera échoue aujourd'hui sans rien
signaler. Un signalement fuite si on n'y prend garde : un projet `professional` ne doit
transmettre aucun texte libre (ADR-043), aucun secret ne sort (ADR-073), les termes interdits
s'arrêtent aussi ici (ADR-050).

## Ce qu'il faut faire

- `valider_signal(args, *, projet, confidentialite, deja_emis_run, deja_emis_jour) ->
  SignalValide | Refus` selon la spec §6. Titre ≤ 120, description ≤ 1 500 caractères,
  `categorie` et `composant` dans leurs énumérations ; 3 par run, 10 par projet et par jour.
- Les gardes de termes interdits et de secrets existantes passent sur `titre` et `description` ;
  un seul hit refuse, avec la raison, sans réécrire le texte.
- Projet `professional` : `titre` fabriqué par le code (`[<rôle>] <categorie> — <composant>`),
  `description` ignorée, source « un projet professionnel ».
- Doublon : clé (`categorie`, `composant`, titre normalisé) sur 7 jours, tenue dans
  `ide_state_dir/signaux_agents.json` ; un doublon refuse « déjà signalé » et incrémente `vu`.

## Critères d'acceptation

- [ ] `test_signal_agent.py::test_valid_signal_is_accepted_with_source_from_the_run`
- [ ] `test_signal_agent.py::test_fourth_signal_of_a_run_is_refused`
- [ ] `test_signal_agent.py::test_eleventh_signal_of_a_day_is_refused`
- [ ] `test_signal_agent.py::test_forbidden_term_and_secret_are_refused_with_a_reason`
- [ ] `test_signal_agent.py::test_professional_project_drops_free_text_and_hides_its_name`
- [ ] `test_signal_agent.py::test_duplicate_is_refused_and_counts_a_view`
- [ ] `test_signal_agent.py::test_oversized_description_is_refused_not_truncated`

## Ce que ça ne fait pas

N'écrit aucun ticket ; n'expose aucun outil à un agent (ticket-863).
