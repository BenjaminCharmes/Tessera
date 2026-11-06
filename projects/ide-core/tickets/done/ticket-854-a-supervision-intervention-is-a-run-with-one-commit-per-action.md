---
agent: codeur
created: 2026-11-05
depends_on:
- ticket-850
- ticket-853
estimated_days: 1
id: ticket-854
pr_number: null
priority: high
status: done
title: A supervision intervention is a run with one commit per action
type: feat
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
  la livraison phase 1 (rebase, push, PR). `refus_de_chemin` (ticket-851) est appliqué au
  diff avant le commit : un fichier hors liste annule tout.
- **La livraison d'une intervention ne passe pas par l'approbation d'un run.** Aucun
  `PipelineResult(approved=True)` n'est fabriqué : le 06/11, une première implémentation le
  faisait et l'audit sécurité l'a bloquée (CRITICAL, « approbation fictive »). `Livraison`
  gagne une méthode dédiée, `livrer_intervention(branche, sha)`, qui :
  - relit elle-même le diff de la branche depuis la base et le soumet à `refus_de_chemin`
    (ticket-851) ; un fichier hors liste, une branche qui ne commence pas par `supervision-`
    ou une tête différente de `sha` : rien n'est poussé ;
  - ouvre la PR et s'arrête là, **quel que soit le niveau d'autonomie** : jamais de merge,
    jamais de remise à `CIWatcher` ;
  - laisse `livrer_phase_1` inchangée : un run non approuvé ne se livre toujours pas (ADR-030).
- Le commit alimente `ajouter_ligne` (ticket-853) avec son SHA.
- Exception, refus de chemin ou commit raté : `blocked` avec commit, jamais d'arbre sale.

## Critères d'acceptation

- [ ] `test_intervention.py::test_intervention_waits_for_the_running_run_then_writes`
- [ ] `test_intervention.py::test_intervention_does_not_write_while_a_queue_holds_the_project`
- [ ] `test_intervention.py::test_intervention_gives_up_after_the_delay_without_writing`
- [ ] `test_intervention.py::test_forbidden_path_in_diff_cancels_everything`
- [ ] `test_intervention.py::test_one_action_makes_one_commit_and_one_journal_line`
- [ ] `test_intervention.py::test_exception_ends_blocked_with_a_commit`
- [ ] `test_intervention_livraison.py::test_delivery_rereads_the_diff_and_refuses_a_forbidden_path`
- [ ] `test_intervention_livraison.py::test_delivery_opens_a_pr_and_never_merges_even_in_merge_autonomy`
- [ ] Le diff ne construit aucun `PipelineResult` avec `approved=True` hors de `services/pipeline/`
      et ne modifie pas la garde `if not approuve` de `livrer_phase_1` (`livraison.py`)

## Ce que ça ne fait pas

N'a aucune action concrète (tickets 855 à 858). Ne merge pas : la livraison s'arrête où le
projet l'autorise.