---
id: ticket-746
title: "Git environment assignments before git or gh are refused"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: ["ticket-745"]
estimated_days: 1
created: 2026-11-03
---

# ticket-746 — Une affectation d'environnement git devant git ou gh se refuse

## Objectif

Le filtre de `-c` (ticket-705) ne se contourne plus par l'environnement.

## Contexte

Audit du 30/10 (relecture du 03/11). `_AFFECTATION` et `sans_prefixe`
(`backend/src/tessera/services/providers/git_guard_lexique.py`) sautent les affectations en
tête de segment sans les examiner. Passent (vérifié) :
`GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.fsmonitor GIT_CONFIG_VALUE_0='x' git status`,
`GIT_CONFIG_PARAMETERS="'core.fsmonitor=./x.sh'" git status`,
`GIT_EXTERNAL_DIFF=./x.sh git diff` — alors que `git -c core.fsmonitor=x status` est refusé.

## Solution proposée

Refuser un segment git ou gh précédé, directement ou derrière `env`, d'une affectation de
`GIT_*`, `GH_*`, `PAGER`, `EDITOR`, `VISUAL` ou `SSH_*`. Les autres affectations restent
admises.

## Critères d'acceptation

- [ ] Un test vérifie que les trois commandes du contexte sont refusées
- [ ] Un test vérifie que `env GIT_EXTERNAL_DIFF=./x.sh git diff` est refusé
- [ ] Un test vérifie que `FOO=bar git status` passe toujours

## Dépendances

ticket-745 (même garde).
