---
id: ticket-807
title: "The test limit and the stay-awake setting are read when they are used"
type: feat
status: todo
pr_number: null
priority: low
agent: codeur
depends_on: ["ticket-806"]
estimated_days: 1
created: 2026-11-05
---

# ticket-807 — La limite de suites de tests et la veille se lisent à l'usage

## Objectif

`max_parallel_test_runs` et `keep_awake_during_runs` se changent sans redémarrage, et plus aucun
module ne lit un réglage modifiable ailleurs que dans `reglages.py`.

## Contexte

ADR-075 et le design, §3. Deux bugs dormants que le changement à chaud réveille : le sémaphore
de `test_runner` est créé une fois, donc une nouvelle limite ne s'y lirait jamais ; et
`eveil.retenir()` comme `eveil.relacher()` consultent le réglage, donc le couper entre les deux
laisserait la machine éveillée pour toujours.

## Ce que le ticket fait

- `services/test_runner.py` : le sémaphore devient un limiteur dont la limite se relit, par
  `reglages.du_moment().max_parallel_test_runs`, à chaque acquisition. Un créneau déjà tenu se garde.
  `reset_semaphore_for_tests` garde sa signature ; les tests du ticket-348 passent sans modification.
- `services/eveil.py` : `retenir` lit `du_moment().keep_awake_during_runs` ; `relacher` ne lit plus
  aucun réglage et relâche toujours.
- Un test de garde interdit `settings.<nom>` pour les cinq noms du registre dans tout fichier de
  `backend/src/`, sauf `reglages.py` et `config.py`.

## Tests

- `backend/tests/test_test_runner_limite_dynamique.py` :
  `test_a_lowered_limit_applies_to_the_next_acquisition`,
  `test_a_slot_held_before_the_change_is_kept`,
  `test_a_limit_of_zero_in_env_still_means_no_bound`
- `backend/tests/test_eveil.py` : `test_retenir_does_nothing_when_the_setting_is_off`,
  `test_relacher_releases_even_when_the_setting_was_turned_off_after_retenir`
- `backend/tests/test_lecture_unique_des_reglages.py` :
  `test_no_module_reads_a_changeable_setting_from_settings`

## Critères d'acceptation

- [ ] Les tests ci-dessus passent ; `backend/tests/test_test_runner*.py` existants inchangés et verts
- [ ] Le test de garde échoue sur un `settings.max_parallel_test_runs` ajouté à la main dans un service

## Ce que ça ne fait pas

Une limite relevée ne réveille pas ceux qui attendent déjà : elle vaut à la prochaine libération
ou acquisition. Dit dans le docstring du limiteur.
