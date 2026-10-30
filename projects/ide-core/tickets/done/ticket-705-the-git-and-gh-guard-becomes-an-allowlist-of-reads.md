---
agent: codeur
created: 2026-10-30
depends_on:
- ticket-703
estimated_days: 1
id: ticket-705
pr_number: null
priority: high
status: done
title: The git and gh guard becomes an allowlist of reads
type: refactor
---

# ticket-705 — Le garde git/gh devient une liste blanche de lectures (C-03)

## Objectif
Le garde git et `gh` n'admet plus que des lectures nommées : toute
sous-commande hors liste est refusée, comme le pose ADR-067.

## Contexte
Audit de sécurité, `docs/audit/securite.md`, constats S-03, S-04, S-05 et S-12.
`backend/src/tessera/services/providers/git_guard.py` tient une liste noire
(`_SOUS_COMMANDES_INTERDITES`, `_SOUS_COMMANDES_GH_INTERDITES`). Ses trous :
- `git bisect run` et `git -c core.fsmonitor=…` exécutent une commande ;
  `git credential fill` livre un secret ;
- dans `gh --repo o/r pr merge`, la sous-commande se cache derrière la valeur
  d'une option ;
- `gh auth token`, `gh alias set`, `gh secret`, `gh run` et `gh issue` ne sont
  pas listés.

ADR-067, dans la section « Proposées » de `memory/contraintes.md`, décide de
passer à une liste blanche.

## Solution proposée
- **git** : une liste blanche de sous-commandes de lecture (`status`, `diff`,
  `log`, `show`, `rev-parse`, `ls-files`, `blame`, `grep`, `describe`,
  `cat-file`, `merge-base`, `shortlog`, `for-each-ref`, `ls-tree`). `branch`
  reste refusé. Les options globales se lisent avant la sous-commande. `-c`
  n'accepte que des clés cosmétiques (`color.*`, `core.quotepath`), pas
  `core.pager`. `--output` est refusé.
- **gh** : les options globales (`--repo` ou `-R <valeur>`, `--hostname`) se
  sautent avant de lire la sous-commande. Seul `gh auth status` reste admis (un
  test existant l'impose), tout le reste est refusé.

## Critères d'acceptation
- [ ] `test_unlisted_git_subcommand_is_refused` (dans `backend/tests/test_git_guard.py`) : `bisect`, `credential`, `commit-tree`, `symbolic-ref`, `update-index`, `gc`, `notes`, `init` sont refusés
- [ ] `test_git_config_override_is_refused_unless_cosmetic` : `git -c core.fsmonitor=x status` est refusé, `git -c color.ui=false status` passe
- [ ] `test_git_output_option_is_refused` : `git diff --output=f` est refusé
- [ ] `test_gh_global_option_does_not_hide_the_subcommand` : `gh --repo o/r pr merge 1` et `gh -R o/r pr merge 1` sont refusés
- [ ] `test_gh_unlisted_subcommand_is_refused` : `gh auth token`, `gh alias set p 'pr merge'`, `gh secret list`, `gh issue create` et `gh run rerun 1` sont refusés ; `gh auth status` passe
- [ ] `test_allowlist_keeps_status_diff_log_show` : `git status`, `git diff HEAD`, `git log --oneline`, `git show HEAD` et `git -C sub status` passent
- [ ] Les tests existants de `backend/tests/test_git_guard.py` ne sont ni supprimés ni affaiblis

## Ce que ça ne fait pas
- Ne touche pas le git que le pipeline lance lui-même (ticket-677)
- Ne déplace pas la règle d'ADR-067 hors de « Proposées » : un agent ne peut
  pas écrire ailleurs dans `contraintes.md`, ce déplacement se fait à la main
  après le merge