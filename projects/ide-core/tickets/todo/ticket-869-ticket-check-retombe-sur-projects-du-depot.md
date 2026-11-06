---
id: ticket-869
title: "ticket_check finds the project in the repository's projects/ when the workspace has none"
type: fix
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-11-06
---

# ticket-869 — `ticket_check` trouve le projet dans `projects/` du dépôt

## Objectif

`python -m tessera.services.projets.ticket_check ide-core` doit trouver le
projet quand on le lance depuis un worktree, pour que la vérification des
tickets marche partout où l'on écrit des tickets.

## Contexte

`main()` de `backend/src/tessera/services/projets/ticket_check.py` cherche le
projet sous `settings.ide_workspace_dir / <id>`. Dans le checkout, `.env`
pose `IDE_WORKSPACE_DIR` sur `projects/` et tout va bien. Dans un worktree
(`~/.tessera/worktrees/manuel/…`), il n'y a pas de `.env` : le réglage retombe
sur son défaut `~/tessera-workspace`, et la commande répond
`projet introuvable : C:\Users\…\tessera-workspace\ide-core` (reproduit le
06/11 dans un worktree détaché de `origin/develop`).

Or c'est justement dans un worktree qu'on écrit les tickets à la main (rien sur
le bureau), donc là que la vérification sert.

## Solution proposée

Une fonction publique `dossier_du_projet(project_id: str) -> Path | None` dans
`ticket_check.py` : d'abord `settings.ide_workspace_dir / project_id`, sinon
`<racine du dépôt>/projects/<project_id>` (la racine du dépôt est celle que
`config.py` calcule déjà, `_REPO_ROOT`), sinon `None`. `main()` l'utilise, et
son message d'erreur cite les deux chemins essayés.

Ne pas changer le défaut de `ide_workspace_dir` dans `config.py` : le backend
et d'autres modules en dépendent.

## Critères d'acceptation

- [ ] `ticket_check.py` définit `dossier_du_projet(project_id)` qui renvoie
      `settings.ide_workspace_dir / project_id` quand ce dossier existe.
- [ ] Un test de `backend/tests/test_ticket_check.py` vérifie que, le dossier
      d'espace de travail ne contenant pas le projet, `dossier_du_projet`
      renvoie `<racine du dépôt>/projects/<id>` quand celui-ci existe.
- [ ] Un test vérifie que `dossier_du_projet` renvoie `None` quand aucun des
      deux dossiers n'existe.
- [ ] `main()` passe par `dossier_du_projet`, et un test vérifie que son
      message d'erreur sur un projet absent contient les deux chemins essayés.
- [ ] Le diff ne modifie pas `backend/src/tessera/config.py`.

## Dépendances

Aucune. Le ticket-870 réutilise `dossier_du_projet`.

## Estimation

Une demi-journée au plus.

## Risques

Un projet du même nom présent dans les deux dossiers : l'espace de travail
déclaré gagne, comme aujourd'hui.

## Ce que ça ne fait pas

Ne touche pas au chargement de `.env` dans les worktrees : les autres
réglages y gardent leur défaut.
