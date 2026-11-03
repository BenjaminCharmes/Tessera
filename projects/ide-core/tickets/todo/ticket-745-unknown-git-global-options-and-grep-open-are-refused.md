---
id: ticket-745
title: "Unknown git global options and git grep --open are refused"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-11-03
---

# ticket-745 — Les options globales git inconnues et `git grep --open` se refusent

## Objectif

Le garde git/gh ne laisse plus une option globale ou une option de `git grep` cacher une
commande hors de la liste blanche.

## Contexte

Audit du 30/10 (relecture du 03/11), ticket-705. Deux contournements confirmés :
- `git --namespace status push` : `_OPTIONS_GIT_AVEC_VALEUR`
  (`backend/src/tessera/services/providers/git_guard_lectures.py`) ne connaît que `-C`,
  `--git-dir`, `--work-tree` ; toute autre option compte pour un seul jeton. Le garde lit
  `status`, git exécute `push` (vérifié : `git --namespace status rev-list -1 HEAD` exécute
  `rev-list`). Idem `--attr-source`.
- `git grep --open="sh -c '…'" -e x` : seuls `-O…` et le nom long exact
  `--open-files-in-pager` sont reconnus ; git accepte les abréviations et les options
  courtes groupées (`-iOx`). Le pager s'exécute hors du garde.

## Solution proposée

- Une option globale git absente d'une liste blanche explicite (`-C`, `--git-dir`,
  `--work-tree`, `--no-pager`, `-P`, `--literal-pathspecs`, `-c` cosmétique déjà filtré…)
  refuse la commande.
- `git grep` : refuser tout préfixe d'au moins 3 caractères de `--open-files-in-pager` et
  tout jeton d'options courtes groupées qui contient `O`.

## Critères d'acceptation

- [ ] Un test vérifie que `git --namespace status push`, `git --attr-source x push` et
      `git --frobnicate status` sont refusés
- [ ] Un test vérifie que `git --no-pager log` et `git -C sub status` passent
- [ ] Un test vérifie que `git grep --open=x foo`, `git grep --open-f=x foo` et
      `git grep -iOx foo` sont refusés, et que `git grep -i foo` passe

## Risques

Une option globale légitime oubliée refusera une lecture : le refus le dit.
