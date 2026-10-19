---
id: ticket-519
title: "A run executes in its worktree, and the checkout is never written"
type: feat
status: todo
priority: medium
agent: codeur
depends_on: ["ticket-515", "ticket-516", "ticket-517", "ticket-518"]
estimated_days: 1
created: 2026-10-19
pr_number: null
---

# ticket-519 — Un run s'exécute dans son worktree

## Objectif
Brancher le worktree dans le cycle de vie du run : un projet qui déclare
`worktree` n'écrit plus jamais dans son checkout.

## Contexte
ADR-056, spec §§ 1, 3 et 5. `_build_orchestrator`
(`routers/orchestrator.py`) construit tout depuis `project_path` ; `RunLock`
est acquis avant `ensure_clean_tree`. La politique se lit sur le dossier réel,
le reste sur le dossier du projet dans le worktree.

## Ce qu'il faut faire
- Quand `politique.worktree` n'est pas `None` : sous `RunLock`, avant
  `ensure_clean_tree`, `creer` puis `peupler` (tickets 516 et 517). Les chemins
  absents du peuplement sont journalisés au journal du pipeline.
- `_build_orchestrator` reçoit le `RunWorktree` : `TicketService`,
  `pipeline_log_path`, `GitWorkspaceService`, `AgentRunner`, `carte_du_depot`,
  `cwd` des agents prennent `wt.projet`. `PolitiqueRun` reste lue sur le dossier
  réel. `PolitiqueRun.racine_ecriture` donne le worktree (ancestor) ou
  `wt.projet`.
- `TestRunnerService` reçoit `commande_effective` et l'environnement du
  ticket-518 ; `test_cwd` s'applique à `wt.projet`.
- `GitWorkspaceService._ensure_own_repository` accepte la racine d'un worktree
  (le `--show-toplevel` y est la racine du worktree).
- `claude_md_ancetres_a_exclure` (`providers/agent_sdk.py`) s'appuie sur
  `racine_ecriture`, pas sur `_REPO_ROOT` : un worktree est hors de ce dépôt.
- Fin de run : après le commit final, et à la fin de la phase 1 de livraison,
  `supprimer`. Elle précède `run_closed`. `TravailNonSauve` met le run en
  `blocked` et nomme le dossier ; il reste. Sur toute exception, le `finally` du
  run appelle la même suppression (ADR-037).
- Vérifier et, au besoin, retirer de la phase 2 (`CIWatcher`) tout appel qui
  lit ou écrit un arbre (`retourner_sur_base`, etc.) : en mode worktree, elle
  n'a que l'API GitHub.
- Une branche déjà extraite dans le checkout, ou un `WorktreeOccupe` : run
  `blocked`, cause dans `arret`, aucun commit à faire (rien n'a été écrit).

## Tests
- [ ] `backend/tests/test_run_dans_un_worktree.py`, dépôt et `origin` locaux, faux provider : un run complet laisse le checkout **identique** (branche, `git status`, fichier écrit à la main intact) et pousse sa branche
- [ ] le fichier écrit à la main dans `tickets/todo/` pendant le run n'est pas dans le commit du run (cas de la PR #508)
- [ ] le worktree n'existe plus après un run approuvé, ni après un run en exception
- [ ] commit final raté → le worktree reste, run `blocked`, `arret` nomme le dossier
- [ ] branche déjà extraite dans le checkout → `blocked`, rien d'écrit
- [ ] `test_perimetre_ecriture.py` : le hook refuse une écriture dans le checkout, accepte le worktree ; chemin de refus identique pour `git_root: ancestor`
- [ ] `test_verrou_par_projet.py` : un second run sur le même projet répond toujours 409
- [ ] projet sans `worktree` : tous les tests existants du pipeline passent, comportement inchangé

## Critères d'acceptation
- [ ] Les huit tests ci-dessus existent et passent
- [ ] `RunLock` est inchangé : la phrase d'ADR-038 « même arbre » devient « même base » dans le commentaire de `run_lock.py`
- [ ] mypy et la suite backend passent

## Dépendances
Tickets 515, 516, 517 et 518.

## Ce que ça ne fait pas
Ni reprise des orphelins (520), ni chat, ni projets `local`, ni activation sur
ide-core : un humain ajoute la clé `worktree` à `agents.json`, que les agents
ne peuvent pas écrire (ADR-027).
