---
id: ticket-520
title: "Worktrees left by a backend stop are saved, then removed at startup"
type: feat
status: todo
priority: medium
agent: codeur
depends_on: ["ticket-522", "ticket-523"]
estimated_days: 0.5
created: 2026-10-19
pr_number: null
---

# ticket-520 — Reprendre les worktrees orphelins au démarrage

## Objectif
Qu'un redémarrage du backend ou du PC ne laisse ni travail perdu ni dossier
traînant, et ne touche jamais le checkout de l'humain.

## Contexte
Spec § 1. `reprise_orphelin.py` (ticket-369) remet d'aplomb le **checkout** d'un
projet dont un run a été interrompu. Avec un worktree, le travail est dans
`<IDE_WORKTREES_DIR>/<projet>/<ticket>` et le checkout n'a pas bougé : l'accident
du 16/10 (checkout laissé sur une branche de run) ne peut plus arriver.

## Ce qu'il faut faire
Fonction `reprendre_worktrees_orphelins(workspace_dir, worktrees_dir)` appelée
dans le lifespan, juste après `reprendre_depots_orphelins` :
- pour chaque dossier `<worktrees_dir>/<projet>/<ticket>` (le `RunRegistry` est
  vide au démarrage : aucun n'a de run vivant) :
  - arbre sale → ajout des modifications suivies et des fichiers non suivis non
    ignorés, commit `_unapproved_commit_message(ticket_id, "run interrupted by a
    backend stop")` (ADR-018, ADR-037) ;
  - `retirer_les_liens` puis suppression (ticket-523) ;
  - un commit raté **laisse** le dossier et journalise (jamais détruire du
    travail non sauvé) ;
- `git worktree prune` sur le dépôt de chaque projet, pour un enregistrement dont
  le dossier a disparu ;
- un dossier qui n'est enregistré par aucun dépôt connu est journalisé et laissé.
- Une erreur n'empêche jamais le démarrage (comme `reprise_orphelin`).
- `reprise_orphelin` inchangé pour les projets sans `worktree`.

## Tests
Dans `backend/tests/test_runs_orphelins.py` (ou un fichier voisin) :
- [ ] worktree sale → commit « unapproved work » sur la branche du ticket, puis dossier supprimé
- [ ] worktree propre → supprimé, sans commit
- [ ] enregistrement dont le dossier a disparu → `prune` le retire
- [ ] commit en échec → le dossier reste, journal, le démarrage continue
- [ ] un worktree dont `node_modules` est un lien : la cible survit
- [ ] le checkout du projet est identique avant et après (branche, `git status`)
- [ ] dossier inconnu des dépôts → laissé, journalisé

## Critères d'acceptation
- [ ] Les sept tests ci-dessus existent et passent
- [ ] Les tests existants de `reprise_orphelin` passent sans modification de leurs assertions

## Dépendances
Tickets 522 et 523.

## Ce que ça ne fait pas
Ne reprend pas la **livraison** d'un run approuvé non livré : c'est le sujet
d'`reprise_orphelin` pour le journal, inchangé.
