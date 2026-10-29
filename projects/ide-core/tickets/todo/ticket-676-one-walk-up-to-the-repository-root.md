---
id: ticket-676
title: "One walk up to the repository root"
type: refactor
status: todo
priority: medium
agent: codeur
depends_on: [ticket-675]
created: 2026-10-29
---

# ticket-676 — Une seule remontée vers le dépôt

## Objectif
Une fonction unique décide quel dossier est la racine d'écriture d'un projet
(`git_root: ancestor`, ADR-028), et une seule façon de dire « ce dossier est un
dépôt ».

## Contexte
Six copies (`docs/audit/doublons.md` §1.2) : `politique_run.py:127`,
`providers/perimetre.py:86`, `providers/agent_sdk.py:105`,
`reprise_orphelin.py:122`, `project_removal.py:136`, `project_overview.py:149`.
Cinq testent `.exists()`, une documente qu'un `.git` fichier (worktree) compte.
`project_removal.py:136` descend au lieu de remonter.

## Critères d'acceptation
- [ ] Une seule fonction remonte vers `.git` ; les cinq autres copies l'appellent
- [ ] Un `.git` fichier (worktree) est traité de la même façon partout, et un test le fige
- [ ] La comparaison à `"ancestor"` n'existe qu'à un endroit (`grep -rn '"ancestor"' backend/src` ne rend que ce module)
- [ ] Le cas de `project_removal.py:136` est soit ramené à la fonction commune, soit laissé tel quel avec un commentaire qui dit pourquoi son sens est inverse
- [ ] `uv run pytest` et `uv run mypy` passent ; les tests existants de `perimetre`, `reprise_orphelin` et `project_overview` ne changent pas

## Ce que ça ne fait pas
- Ne change pas le périmètre d'écriture d'un run (ADR-031)
- Ne touche pas aux fichiers de `git_workspace/` qui n'utilisent pas la remontée
