---
agent: codeur
created: 2026-10-02
depends_on: []
estimated_days: 1
id: ticket-314
pr_number: null
priority: critical
status: done
title: A run never continues without its branch in a git repository, and pending bookkeeping
  never blocks the checkout
type: fix
---

# ticket-314 — Un run ne continue jamais sans sa branche

## Objectif

Qu'un ticket ne soit plus jamais codé, relu et approuvé sur la branche d'un
autre, ni sans branche du tout.

## Contexte

Deux fois le 2026-10-02, un ticket a tourné sans sa propre branche :

- `carriere`, ticket-017 : pas de `branch_created`, `pipeline_done` avec
  `branch: null`, aucun commit. La livraison a répondu « Aucune branche :
  rien à livrer », et le travail approuvé est resté non commité dans l'arbre,
  sur la branche du ticket-016. Il a fallu le sauver à la main.
- `ide-core`, ticket-306 : même absence de branche, la file arrêtée à temps.

Les deux suivaient une livraison interrompue : un 405 au merge pour le 016,
un conflit de rebase pour le 305. Le journal du pipeline
(`memory/pipeline-log.md`, versionné dans ces deux projets) restait alors
modifié dans l'arbre. Le `git checkout -b` du ticket suivant, qui part d'une
base où ce fichier diffère, a été refusé par git, qui protège une
modification locale.

`pipeline_stages.create_branch` (vers la ligne 76) attrapait **toute**
`GitWorkspaceError` et poursuivait avec un simple avertissement. Ce repli était
prévu pour un projet sans dépôt git : sur un dépôt réel, il fait coder le
ticket sur la branche courante, celle du ticket précédent.

## Solution proposée

- Seule l'absence de dépôt (`NotAGitRepository`, ou équivalent) garde le
  repli sans branche. Toute autre `GitWorkspaceError` pendant la création de
  branche termine le run en `blocked`, avec un `arret` qui cite l'erreur git
  (ADR-037), sans appeler aucun agent.
- Avant de créer la branche d'un nouveau ticket, les artefacts de tenue de
  livres en attente (le journal, les fichiers ticket) sont commités sur la
  branche courante (`commit_bookkeeping`), pour que le checkout ne bute plus
  sur eux.

## Critères d'acceptation

- [x] Un test vérifie qu'une `GitCommandError` levée par `create_branch` sur
      un dépôt réel termine le run en `blocked`, avec un `arret` qui contient
      le message git, et qu'aucun agent n'est appelé
- [x] Un test vérifie qu'un projet sans dépôt git (`NotAGitRepository`)
      continue sans branche, comme aujourd'hui
- [x] Un test sur un dépôt git temporaire reproduit le cas : journal modifié
      dans l'arbre, base où il diffère, puis nouveau ticket. Il vérifie que
      la branche du ticket est créée, et que la modification du journal est
      commitée sur la branche précédente
- [x] Un test vérifie qu'un fichier de **code** modifié dans l'arbre empêche
      toujours la création de branche (`blocked`), au lieu d'être commité

## Dépendances

Aucune.

## Risques

Commiter la tenue de livres sur la branche du ticket précédent ajoute un
commit à une branche dont la PR est peut-être déjà ouverte : c'est un commit
`chore: tessera pipeline bookkeeping`, qui suit le même chemin que ceux
d'aujourd'hui.

## Ce que ça ne fait pas

- `commit_bookkeeping` avant le checkout est non-fatal : si le commit échoue
  (pas de config git, pas de HEAD), le pipeline tente quand même le checkout.
  Un fichier de code sale déclenche malgré tout un `blocked` via `GitCommandError`.
- `ensure_clean_tree` reste le garde-fou amont pour les modifications de code
  hors pipeline ; `create_branch` n'en est que le filet de sécurité aval.