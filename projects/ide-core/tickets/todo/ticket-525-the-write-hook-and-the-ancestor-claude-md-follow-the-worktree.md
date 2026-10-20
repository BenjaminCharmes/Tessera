---
id: ticket-525
title: "The write hook and the ancestor CLAUDE.md exclusion follow the worktree"
type: feat
status: todo
priority: medium
agent: codeur
depends_on: ["ticket-521"]
estimated_days: 0.5
created: 2026-10-19
pr_number: null
---

# ticket-525 — Le hook d'écriture et les CLAUDE.md d'ancêtres suivent le worktree

## Objectif
Que le périmètre d'écriture, la vérification de dépôt et l'exclusion des
`CLAUDE.md` d'ancêtres sachent désigner un worktree, avant que le run n'en
utilise un. Pièces séparées du branchement (ticket-519) pour qu'il reste court.

## Contexte
ADR-056, spec § 3. Le hook d'écriture (ADR-031) tient sa racine de
`PolitiqueRun.racine_ecriture` ; `GitWorkspaceService._ensure_own_repository`
applique ADR-024 ; `claude_md_ancetres_a_exclure` (`providers/agent_sdk.py`)
calcule depuis `_REPO_ROOT`, or un worktree est **hors** de ce dépôt.

## Ce qu'il faut faire
- `PolitiqueRun.racine_ecriture` accepte un `RunWorktree | None` : avec un
  worktree, la racine est `wt.racine` (projet `ancestor`) ou `wt.projet`. Sans,
  comportement inchangé. La résolution des liens des deux côtés est conservée.
- `GitWorkspaceService._ensure_own_repository` accepte la racine d'un worktree :
  `--show-toplevel` y renvoie la racine du worktree, et ne doit pas exiger
  `git_root: ancestor`. Un dossier qui n'est ni le projet, ni son ancêtre
  déclaré, ni un worktree de ce dépôt reste refusé (`NotAGitRepository`).
- `claude_md_ancetres_a_exclure` s'appuie sur la racine d'écriture reçue, pas
  sur `_REPO_ROOT`.

## Tests
- [ ] `backend/tests/test_perimetre_ecriture.py` : avec un worktree, le hook refuse une écriture dans le checkout et accepte le worktree ; même refus pour un projet `git_root: ancestor`
- [ ] `backend/tests/test_politique_run.py` : `racine_ecriture` sans worktree est identique à aujourd'hui ; avec, elle vaut `wt.racine` ou `wt.projet`
- [ ] `backend/tests/test_git_workspace.py` : `_ensure_own_repository` accepte un worktree du dépôt, refuse un dossier étranger
- [ ] `backend/tests/test_agent_sdk_consignes_ancetres.py` : avec une racine d'écriture hors de `_REPO_ROOT`, les `CLAUDE.md` d'ancêtres sont exclus depuis cette racine

## Critères d'acceptation
- [ ] Les quatre blocs de tests ci-dessus existent et passent
- [ ] Les tests existants de ces quatre fichiers passent sans modification de leurs assertions
- [ ] Le diff ne modifie ni `backend/src/tessera/services/pipeline_stages.py` ni `backend/src/tessera/services/orchestrator.py` : le branchement est le ticket-519

## Dépendances
Ticket 521. `RunWorktree` vient du ticket-522 : s'il n'est pas mergé, le
paramètre se type par la racine (`Path`), sans importer le module.

## Ce que ça ne fait pas
Ne crée aucun worktree, ne branche pas l'orchestrateur.
