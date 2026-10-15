---
id: ticket-448
title: "The validator finds a cited file anywhere in the repository of a git_root ancestor project"
type: fix
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-15
---

# ticket-448 — Le validateur trouve un fichier cité dans le dépôt ancêtre

## Objectif

Sur un projet déclaré `git_root: ancestor` (ide-core), un fichier cité
entre backticks dans un critère est trouvé et joint au validateur même
s'il vit hors du dossier du projet.

## Contexte

Le ticket-446 s'est bloqué après trois tours (15/10) : ses critères 1 à 3
étaient satisfaits, mais le journal disait « absents :
git_workspace.py, git ls-files CLAUDE.md,
test_run_interrompu_arbre_propre.py ». Le critère « les tests existants de
ce fichier sont inchangés » portait sur un fichier hors du diff : faute de
pouvoir le lire, le validateur a refusé trois fois.

Cause : `_find_file_in_project` dans
`backend/src/tessera/services/validator_cited_files.py` cherche sous
`project_root`, c'est-à-dire `projects/ide-core/`. Le code d'ide-core vit
dans `backend/` et `frontend/`, à la racine du dépôt ancêtre.

Second défaut, vu dans la même ligne : `extract_file_refs` prend
`git ls-files CLAUDE.md` pour un nom de fichier, parce que le texte finit
par une extension.

## Solution proposée

- Quand le projet déclare `git_root: ancestor`, chercher les fichiers cités
  sous la racine du dépôt git qui contient le projet, avec la même borne de
  sécurité (aucun fichier hors de cette racine, aucun chemin absolu).
- `extract_file_refs` ignore un texte entre backticks qui contient une
  espace.

## Critères d'acceptation

- [ ] Un test de `backend/tests/` crée un dépôt avec `projects/p/` et
      `backend/x.py`, cite `x.py` dans un critère pour le projet `p` déclaré
      ancestor, et vérifie que le rapport le classe dans `joined`
- [ ] Un test vérifie que, pour un projet sans `git_root: ancestor`, un
      fichier hors du dossier du projet reste `absent`
- [ ] Un test vérifie qu'un chemin `../../.env` reste refusé dans les deux
      cas
- [ ] Un test vérifie que `extract_file_refs` ignore
      `git ls-files CLAUDE.md`

## Ce que ça ne fait pas

- Ne change pas le budget de 20 000 caractères des fichiers joints.
