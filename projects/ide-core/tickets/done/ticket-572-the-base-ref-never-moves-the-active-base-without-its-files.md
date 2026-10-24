---
agent: codeur
created: 2026-10-24
depends_on: []
estimated_days: 0.5
id: ticket-572
pr_number: null
priority: critical
status: done
title: Initialising the base ref never moves the checked-out base branch without its
  files
type: fix
---

# ticket-572 — La base active n'avance jamais sans ses fichiers

## Objectif
Qu'un run ne commite jamais la suppression de fichiers que la base distante
vient d'ajouter.

## Contexte
Le 24/10, le run du ticket-076 d'Affût a commité la suppression des tickets
077 à 080 (commit `5a4869b`), mergée ensuite sur `main` : la file suivante a
échoué sur « Ticket introuvable : ticket-077 ».

Cause (reflog d'affut et événements du run) : le `main` local actif avait un
commit de retard sur `origin/main` (PR #104 mergée sans `pull`). Le ticket-076
manquait sur le disque, donc `restaurer_ticket_depuis_base`
(`services/git_workspace/ticket_sur_base.py`) a appelé `initialiser_base_ref`
(`services/git_workspace/base.py`), qui avance la base par
`git update-ref refs/heads/main <FETCH_HEAD>` (vers la ligne 153) **sans
vérifier que `main` est la branche active**. La référence avance, l'index et
l'arbre restent ceux de l'ancien `main` : ce que le nouveau commit ajoutait
apparaît comme suppression indexée. `create_branch` part du même commit (git
ne touche pas l'index), puis `commit_all` emporte l'index entier.

`sync_base_depuis_distant` (`services/git_workspace/synchro.py`) avait le
même défaut, corrigé au ticket-390 : sur la base active, il passe par
`_avancer_base_active` (`merge --ff-only`). `initialiser_base_ref` n'a pas reçu
ce correctif.

## Solution proposée
Dans `initialiser_base_ref` : si `branche_courante()` est la branche de base,
avancer par `_avancer_base_active`, et ne garder `update-ref` que quand une
autre branche est active. Si l'avance rapide est refusée (fichier non suivi
qui serait écrasé…), renvoyer la raison et bloquer le run avant
`create_branch`, comme pour la synchro.

## Critères d'acceptation
- [ ] Dans `initialiser_base_ref` de `backend/src/tessera/services/git_workspace/base.py`, la base active avance par `_avancer_base_active`, et `update-ref` n'est appelé que quand une autre branche est active
- [ ] Un test de `backend/tests/test_ticket_ajoute_sur_la_base.py` crée un dépôt et son distant, ajoute `tickets/todo/ticket-a.md` et `tickets/todo/ticket-b.md` sur le distant, laisse le `main` local actif en retard d'un commit, appelle `restaurer_ticket_depuis_base("ticket-a")` puis `create_branch`, et vérifie que `git diff --cached --name-status HEAD` est vide
- [ ] Le même scénario poursuivi jusqu'à `commit_all` produit un commit qui ne supprime pas `tickets/todo/ticket-b.md`, et un test le vérifie
- [ ] Un test vérifie qu'une avance rapide refusée sur la base active rend une raison et n'avance pas la référence par `update-ref`
- [ ] Les tests existants de `sync_base_depuis_distant` restent inchangés dans le diff

## Ce que ça ne fait pas
- Ne restaure pas les tickets d'Affût : c'est fait à la main (PR affut#106).