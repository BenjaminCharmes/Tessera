---
id: ticket-703
title: "The git guard reads the real first word of a segment"
type: fix
status: todo
pr_number: null
priority: critical
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-30
---

# ticket-703 — Le garde git lit le premier mot réel d'un segment (C-01)

## Objectif
Qu'un `git push` précédé d'une affectation de variable ou d'un mot-clé de shell,
ou lancé par `cmd`, `powershell` ou `pwsh`, soit refusé comme le `git push` nu.

## Contexte
Audit de sécurité, `docs/audit/securite.md`, constats S-01 (CRITICAL) et S-06.
`_segment_interdit` (`backend/src/tessera/services/providers/git_guard.py`) lit le
premier jeton du segment. Pour `GIT_AUTHOR_NAME=x git commit`, ce jeton rend le
nom `git_author_name=x`, que rien ne reconnaît, et la fonction rend `False`. Les
mots-clés `then`, `do`, `else`, `{` et `!` sont pris pour le nom de la commande :
`if true; then git push; fi` passe. `SHELLS`
(`backend/src/tessera/services/providers/git_guard_lexique.py`) ne connaît ni
`cmd`, ni `powershell`, ni `pwsh`, alors que Tessera tourne sous Windows.

## Solution proposée
Dans `git_guard_lexique.py` :
- sauter en tête de segment les affectations `NOM=valeur` (le motif existe déjà
  dans `_JETON_D_ENVELOPPE`) et les mots-clés de shell qui introduisent une
  commande ;
- traiter `cmd /c` (et `/k`), et `powershell` ou `pwsh` suivis de `-Command` ou
  `-c`, comme des shells dont la ligne suivante se relit.

`git_guard.py` ne change que pour appeler ce déballage. À faire avant
ticket-705, qui réécrit le même fichier.

## Critères d'acceptation
- [ ] `test_leading_assignment_is_skipped` (dans `backend/tests/test_git_guard.py`) : `FOO=bar git push` et `A=1 B=2 git commit -m x` sont refusés
- [ ] `test_shell_keywords_are_skipped` : `if true; then git push; fi`, `for x in a; do git push; done`, `{ git push; }` et `! git push` sont refusés
- [ ] `test_cmd_and_powershell_are_unwrapped` : `cmd /c git push`, `powershell -Command "git push"` et `pwsh -c "git push"` sont refusés
- [ ] `test_reads_behind_an_assignment_still_pass` : `FOO=bar git status` et `then git log` passent
- [ ] Les tests existants de `backend/tests/test_git_guard.py` ne sont ni supprimés ni affaiblis

## Ce que ça ne fait pas
- Ne passe pas à la liste blanche : c'est ticket-705 (ADR-067)
- Ne prétend pas arrêter une évasion délibérée (ADR-027, ADR-031)

## Risques
Un faux refus prive l'agent de ses lectures. Le quatrième critère protège ce cas.
