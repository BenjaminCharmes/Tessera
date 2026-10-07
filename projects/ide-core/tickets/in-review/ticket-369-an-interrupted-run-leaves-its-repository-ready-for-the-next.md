---
agent: codeur
created: 2026-10-07
depends_on: []
estimated_days: 1
id: ticket-369
pr_number: null
priority: high
status: in-review
title: At startup, a run interrupted by a stop leaves its repository ready for the
  next run
type: fix
---

# ticket-369 — Au démarrage, un run interrompu remet son dépôt d'aplomb

## Objectif

Qu'un redémarrage du PC ou du backend en plein run ne demande plus de
remettre le dépôt en état à la main avant de relancer.

## Contexte

`solder_les_runs_orphelins` (`backend/src/tessera/services/database.py`,
ticket-177) clôt en base, au démarrage, chaque run resté sans `finished_at`.
Le dépôt du projet, lui, reste tel que le processus tué l'a laissé. Constaté
le 2026-10-07 après un redémarrage du PC pendant le ticket-365 :

- l'arbre était sale sur la branche du ticket (le travail du codeur, non
  commité) ;
- la fiche du ticket était restée dans `tickets/in-review/` ;
- la copie de travail était toujours sur la branche du ticket. Or un run
  prend `HEAD` comme base de ses branches (`create_branch`,
  `backend/src/tessera/services/git_workspace.py`) : relancé tel quel, le
  ticket suivant serait parti du travail inachevé.

Tout a dû être remis d'aplomb à la main.

## Solution proposée

Après `solder_les_runs_orphelins`, pour chaque run soldé (`project_id`,
`ticket_id` de `pipeline_runs`), si la copie de travail du projet est sur une
branche `<ticket_id>-…` :

1. commiter les changements en cours sur cette branche avec le message des
   runs non approuvés (`_unapproved_commit_message`,
   `backend/src/tessera/services/pipeline_text.py`), raison « run interrupted
   by a backend stop » — ADR-018 : l'arbre ne reste jamais sale ;
2. remettre la fiche du ticket en `todo` (dossier **et** champ) si elle est en
   `in-progress` ou `in-review` ;
3. revenir sur la branche de base du projet, celle que la livraison utilise.

Si la copie de travail est sur une autre branche, ne rien toucher. Une erreur
git est journalisée et n'empêche jamais le démarrage du backend.

## Critères d'acceptation

- [ ] Un test de `backend/tests/test_reprise_run_orphelin.py` crée un dépôt git temporaire sur une branche `ticket-901-…` avec un fichier modifié, et vérifie qu'après la reprise l'arbre est propre et que le dernier commit de cette branche porte le message de travail non approuvé
- [ ] Un test de `backend/tests/test_reprise_run_orphelin.py` vérifie qu'une fiche de ticket dans `tickets/in-review/` revient dans `tickets/todo/` avec `status: todo`
- [ ] Un test de `backend/tests/test_reprise_run_orphelin.py` vérifie qu'après la reprise la copie de travail est sur la branche de base
- [ ] Un test de `backend/tests/test_reprise_run_orphelin.py` vérifie que si la copie de travail est sur une autre branche que celle du ticket, aucun commit n'est ajouté et la branche ne change pas
- [ ] Un test de `backend/tests/test_reprise_run_orphelin.py` vérifie qu'une erreur git pendant la reprise est journalisée sans lever d'exception
- [ ] `backend/src/tessera/main.py` appelle la reprise dans le `lifespan`, après `solder_les_runs_orphelins`

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

Agir sur un dépôt au démarrage touche au travail de l'utilisateur : d'où la
condition stricte (branche du ticket du run soldé) et aucun `reset`, aucun
`checkout` forcé, aucune suppression.

## Ce que ça ne fait pas

- Ne relance pas le run : l'utilisateur ou la file le relance.
- Ne pousse rien.