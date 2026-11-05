---
id: ticket-854
title: "A supervision intervention is a run with one commit per action"
type: feat
status: todo
priority: high
agent: codeur
depends_on: [ticket-850, ticket-853]
estimated_days: 1
created: 2026-11-05
pr_number: null
---

# ticket-854 — Une intervention du superviseur est un run, un commit par action

## Objectif

`intervenir(project_id, action, appliquer)` donne au superviseur le seul chemin d'écriture : un
run `supervision` sous `RunLock`, sur sa branche, livré comme un run.

## Contexte

ADR-080, spec §5. Le superviseur écrit dans un arbre que des runs et des files occupent : il ne
doit ni les doubler ni les faire échouer en 409. ADR-038 (un run par projet), ADR-018 (branche,
commit), ADR-051 (livraison), ADR-056 (worktree), ADR-037 (toute exception finit en `blocked`
avec commit).

## Ce qu'il faut faire

- `services/supervision/intervention.py` : `intervenir(...)` selon la spec §6. Projet tenu par
  une file (`projet_tenu_par_file`, ticket-850) ou occupé : l'intervention attend la fermeture
  (`RUN_REGISTRY.sur_fermeture`), modèle `signalements_en_attente` ; délai maximal de 30 min,
  passé lequel elle abandonne en journalisant, sans rien écrire.
- Le run `supervision` suit le chemin d'un run : worktree, branche `supervision-<horodatage>`,
  un commit par action (message `chore(supervision): <action> <cible>`, anglais), puis
  la livraison phase 1 au niveau d'autonomie du projet. `refus_de_chemin` (ticket-851) est
  appliqué au diff avant le commit : un fichier hors liste annule tout.
- Le commit alimente `ajouter_ligne` (ticket-853) avec son SHA.
- Exception, refus de chemin ou commit raté : `blocked` avec commit, jamais d'arbre sale.

## Critères d'acceptation

- [ ] `test_intervention.py::test_intervention_waits_for_the_running_run_then_writes`
- [ ] `test_intervention.py::test_intervention_does_not_write_while_a_queue_holds_the_project`
- [ ] `test_intervention.py::test_intervention_gives_up_after_the_delay_without_writing`
- [ ] `test_intervention.py::test_forbidden_path_in_diff_cancels_everything`
- [ ] `test_intervention.py::test_one_action_makes_one_commit_and_one_journal_line`
- [ ] `test_intervention.py::test_exception_ends_blocked_with_a_commit`

## Ce que ça ne fait pas

N'a aucune action concrète (tickets 855 à 858). Ne merge pas : la livraison s'arrête où le
projet l'autorise.
