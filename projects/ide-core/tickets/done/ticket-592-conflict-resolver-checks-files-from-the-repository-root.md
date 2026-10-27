---
agent: codeur
created: 2026-10-26
depends_on: []
estimated_days: 0.25
id: ticket-592
pr_number: 664
priority: high
status: done
title: The conflict resolver checks and stages the resolved files from the repository
  root
type: fix
---

# ticket-592 — Le résolveur de conflit vérifie les fichiers depuis la racine du dépôt

## Objectif
Qu'un conflit de rebase sur un projet `git_root: ancestor` (ide-core) puisse
être résolu : aujourd'hui, le résolveur échoue toujours.

## Contexte
Le 26/10, la livraison du ticket-582 a buté sur un conflit de deux lignes
d'import dans `frontend/src/components/BureauView/Piece.tsx`. Le résolveur a
renoncé : « fichier introuvable après résolution :
frontend/src/components/BureauView/Piece.tsx ». La file s'est arrêtée, et la
résolution a été faite à la main (PR #661).

Cause : dans `backend/src/tessera/services/git_workspace/conflits.py`,
`_raison_fichiers_resolus` construit `self._project_path / chemin`. Or
`chemin` vient de `git diff --name-only --diff-filter=U`, qui renvoie des
chemins **relatifs à la racine du dépôt**. Pour ide-core, `_project_path` est
`projects/ide-core` : le fichier cherché n'existe pas. Le
`git add -- *conflits` qui suit, lancé avec le dossier du projet comme cwd,
viserait lui aussi un mauvais chemin. Le même fichier lit déjà les versions
avec `:/` (ligne ~124) parce que les chemins sont relatifs à la racine : la
vérification et le `git add` ont été oubliés.

## Solution proposée
Résoudre les chemins des conflits depuis la racine du dépôt
(`git rev-parse --show-toplevel`), pour la vérification de présence et de
marqueurs, et passer à `git add` des pathspecs `:/<chemin>`. Un projet dont la
racine est le dépôt (cas normal) garde le même comportement.

## Critères d'acceptation
- [ ] Sur un dépôt de test où le projet est un sous-dossier (`git_root: ancestor`), un conflit sur un fichier hors du dossier du projet, résolu par un résolveur double, termine le rebase ; un test le vérifie
- [ ] Sur ce même dépôt, un fichier résolu qui garde ses marqueurs fait toujours annuler, avec « marqueurs de conflit restants » ; un test le vérifie
- [ ] Sur un projet dont la racine est le dépôt, les tests existants de `conflits.py` restent verts
- [ ] Le diff ne modifie aucun fichier de `frontend/`