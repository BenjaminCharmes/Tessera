---
id: ticket-999
title: "The chat refuses to run a project that declares a worktree"
type: fix
status: todo
priority: high
agent: codeur
depends_on: []
preuve_reelle: true
---

## Signalement

- Audit sans contexte du 17/11, constat M1 (MEDIUM, relevé en priorité haute :
  il ouvre le checkout de l'utilisateur au compte agent).

## Contexte

`routers/chat.py` (`/chat/run`) appelle `build_orchestrator(project_id)` sans
worktree. Pour un projet `compte_agent`, `assemblage_run` considère le run
isolé alors que sa racine est le checkout : `ouvrir_appel` remonte au premier
`.git` et `poser_ecriture` donne `(OI)(CI)M` au compte agent sur le checkout
de l'utilisateur, `.env` compris, et coupe l'héritage du `.git` principal
(`/inheritance:d`), définitivement. ADR-056 : jamais de run dans le checkout
d'un projet qui déclare `worktree`.

## Ce qu'il faut faire

- `/chat/run` refuse (409, message clair) un projet qui déclare `worktree`.
- `ouvrir_appel` refuse une racine hors de `IDE_WORKTREES_DIR` (échec fermé),
  pour qu'aucun autre chemin ne puisse ouvrir le checkout au compte.

## Critères d'acceptation

- [ ] Test : `/chat/run` sur un projet `worktree` → 409, aucun appel lancé.
- [ ] Test : `ouvrir_appel` sur un dossier hors du dossier des worktrees →
      refus, aucun `icacls`.

## Ce que ça ne fait pas

- Ne donne pas de worktree au chat.
