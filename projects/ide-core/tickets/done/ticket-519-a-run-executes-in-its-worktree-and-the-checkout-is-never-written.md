---
agent: codeur
created: 2026-10-19
depends_on:
- ticket-521
- ticket-522
- ticket-523
- ticket-524
- ticket-525
estimated_days: 0.75
id: ticket-519
pr_number: null
priority: medium
status: done
title: A run executes in its worktree, and the checkout is never written
type: feat
---

# ticket-519 — Un run s'exécute dans son worktree

## Objectif
Brancher le worktree dans le cycle de vie du run : un projet qui déclare
`worktree` n'écrit plus jamais dans son checkout.

## Contexte
ADR-056, spec §§ 1, 3 et 5. `_build_orchestrator`
(`routers/orchestrator.py`) construit tout depuis `project_path` ; `RunLock`
est acquis avant `ensure_clean_tree`. La politique se lit sur le dossier réel,
le reste sur le dossier du projet dans le worktree. Les pièces sont livrées :
création (522), peuplement (523), commande de test (524), hook et vérification
de dépôt (525).

## Ce qu'il faut faire
- Quand `politique.worktree` n'est pas `None` : sous `RunLock`, avant
  `ensure_clean_tree`, `creer` puis `peupler` (tickets 522 et 523). Les chemins
  absents du peuplement sont journalisés au journal du pipeline.
- `_build_orchestrator` reçoit le `RunWorktree` : `TicketService`,
  `pipeline_log_path`, `GitWorkspaceService`, `AgentRunner`, `carte_du_depot`,
  `cwd` des agents prennent `wt.projet`. `PolitiqueRun` reste lue sur le dossier
  réel ; sa `racine_ecriture` reçoit le worktree (ticket-525).
- `TestRunnerService` reçoit `commande_effective` et l'environnement du
  ticket-524 ; `test_cwd` s'applique à `wt.projet`.
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
- [ ] même fichier : le fichier écrit à la main dans `tickets/todo/` pendant le run n'est pas dans le commit du run (cas de la PR #508)
- [ ] même fichier : le worktree n'existe plus après un run approuvé, ni après un run en exception
- [ ] même fichier : commit final raté → le worktree reste, run `blocked`, `arret` nomme le dossier
- [ ] même fichier : branche déjà extraite dans le checkout → `blocked`, rien d'écrit
- [ ] `test_verrou_par_projet.py` : un second run sur le même projet répond toujours 409
- [ ] projet sans `worktree` : tous les tests existants du pipeline passent, comportement inchangé

## Critères d'acceptation
- [ ] Les sept tests ci-dessus existent et passent
- [ ] Dans `backend/src/tessera/services/run_lock.py`, le diff ne touche qu'un commentaire, où « même arbre » (ADR-038) devient « même base »
- [ ] mypy et la suite backend passent

## Dépendances
Tickets 521, 522, 523, 524 et 525.

## Ce que ça ne fait pas
Ni reprise des orphelins (520), ni chat, ni projets `local`, ni activation sur
ide-core : un humain ajoute la clé `worktree` à `agents.json`, que les agents
ne peuvent pas écrire (ADR-027).