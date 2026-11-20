---
agent: codeur
created: 2026-11-05
depends_on:
- ticket-851
estimated_days: 1
id: ticket-857
pr_number: null
priority: high
status: done
title: The supervisor hands an unwatched green PR back to CIWatcher
type: feat
---

# ticket-857 — Le superviseur redonne à `CIWatcher` une PR que personne ne surveille

## Objectif

Une PR d'un run approuvé, laissée sans surveillance par une coupure, reprend le chemin normal
de merge, sans que le superviseur merge lui-même.

## Contexte

ADR-080, spec §2 (`reconfier_pr`). Le 05/11 à 11:20, « ticket-776 PR #913 non surveillée
(livraison arrêtée) » ; le 04/11, la livraison de ticket-753 a été coupée par un
`GitCommandError`. Aujourd'hui une session reprend la PR à la main. ADR-039 : `CIWatcher` ne merge
qu'une PR dont la tête relue est encore `pushed_sha`.

## Ce qu'il faut faire

- `services/supervision/superviseur_pr.py`, sans modèle : repérer les runs approuvés dont la PR est
  ouverte, absente de `CIWatcher.en_attente(project_id)` et dont `Livraison.arret` est une
  coupure d'infrastructure (réseau, git, veille) ; jamais une CI rouge (ADR-051), jamais un
  run non approuvé (ADR-030), jamais la PR d'un `resolveur-conflit` (ADR-033).
- Garde : la tête de la PR est `pushed_sha` ; sinon `a_toi`.
- Action : `CIWatcher.surveiller(...)`, une fois par `(PR, sha)` (clé d'idempotence). Aucun
  appel `gh pr merge`, aucun push.

## Critères d'acceptation

- [ ] `test_superviseur_pr.py::test_unwatched_approved_pr_is_handed_to_the_watcher`
- [ ] `test_superviseur_pr.py::test_head_moved_since_pushed_sha_goes_to_a_toi`
- [ ] `test_superviseur_pr.py::test_red_ci_is_never_handed_back`
- [ ] `test_superviseur_pr.py::test_conflict_resolver_pr_is_never_handed_back`
- [ ] `test_superviseur_pr.py::test_same_pr_and_sha_is_handed_once`
- [ ] `test_superviseur_pr.py::test_module_never_calls_a_merge_or_a_push`

## Ce que ça ne fait pas

Ne merge pas. Ne relance pas un run. Ne relit pas la PR.