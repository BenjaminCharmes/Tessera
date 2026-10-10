---
agent: codeur
created: 2026-10-10
depends_on: []
estimated_days: 0.5
id: ticket-396
pr_number: null
priority: high
status: done
title: 'Automatic rebase conflict resolution works for a project nested in its repository
  (git_root: ancestor)'
type: fix
---

# ticket-396 — La résolution des conflits de rebase marche dans un projet imbriqué

## Objectif

Que les conflits sur les artefacts Tessera (fiches de tickets, journal) se
résolvent seuls au rebase de livraison sur ide-core, comme sur un projet à la
racine de son dépôt.

## Contexte

`GitWorkspaceService._resoudre_conflits_artefacts`
(`backend/src/tessera/services/git_workspace.py`, ticket-300) reçoit les
chemins en conflit de `git diff --name-only --diff-filter=U` : ils sont
**relatifs à la racine du dépôt**. Il lance ensuite
`git status --porcelain -- <chemin>`, `git checkout --theirs -- <chemin>` et
`git add -- <chemin>` avec le dossier du projet comme cwd. Pour un projet
déclaré `git_root: ancestor` (ide-core, dans `projects/ide-core/`), ces
pathspecs sont résolus **depuis le cwd** et ne désignent aucun fichier :
`checkout --theirs` échoue, la résolution rend `False`, et la livraison
s'arrête sur « Conflit avec develop ».

Constaté le 2026-10-09 : livraison du ticket-388 arrêtée sur un conflit de
fiche (`tickets/done/ticket-387-…`), un cas que le ticket-300 devait
résoudre seul. Le même défaut touchait l'union des journaux du ticket-391,
corrigé le 2026-10-10 par `:/<chemin>` (PR #349).

## Solution proposée

Dans `_resoudre_conflits_artefacts`, désigner chaque fichier en conflit par le
pathspec `:/<chemin>` (relatif à la racine du dépôt) pour `status`, `rm`,
`checkout --theirs` et `add`. Vérifier les autres appels de
`git_workspace.py` qui réutilisent des chemins issus de `git diff
--name-only` ou `git status --porcelain` avec le cwd du projet, et les
corriger de la même façon.

## Critères d'acceptation

- [ ] Un test de `backend/tests/test_git_workspace.py` crée un vrai dépôt dont le projet est un sous-dossier (`projects/p/`, `git_root: ancestor`), provoque au rebase un conflit sur `projects/p/tickets/done/ticket-001.md` seul, et vérifie que `rejouer_sur` aboutit sans conflit restant
- [ ] Un test de `backend/tests/test_git_workspace.py` vérifie, dans le même dépôt imbriqué, qu'un conflit sur `projects/p/memory/pipeline-log.md` se résout en union (ticket-391)
- [ ] Un test de `backend/tests/test_git_workspace.py` vérifie que, dans le dépôt imbriqué, un conflit qui touche aussi un fichier de code n'est pas résolu automatiquement et rend ce fichier dans la liste des conflits
- [ ] Les tests existants de résolution des conflits d'artefacts (projet à la racine du dépôt) passent sans modification

## Dépendances

Aucune.

## Estimation

0,5 jour.

## Risques

Aucun pour un projet à la racine de son dépôt : `:/<chemin>` y désigne le
même fichier que `<chemin>`.

## Ce que ça ne fait pas

- N'élargit pas la liste des fichiers résolus automatiquement.