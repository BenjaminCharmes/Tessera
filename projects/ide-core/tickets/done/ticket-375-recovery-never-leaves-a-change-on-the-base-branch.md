---
agent: codeur
created: 2026-10-07
depends_on: []
estimated_days: 0.5
id: ticket-375
pr_number: null
priority: high
status: done
title: Startup recovery resets the ticket on its own branch and never leaves a change
  on the base branch
type: fix
---

# ticket-375 — La reprise ne laisse jamais de changement sur la branche de base

## Objectif

Qu'après une reprise au démarrage (ticket-369), le run suivant du projet
démarre normalement, sans être bloqué par sa propre base.

## Contexte

`backend/src/tessera/services/reprise_orphelin.py` commite le travail du run
interrompu sur la branche du ticket, revient sur la branche de base, **puis**
remet la fiche du ticket en `todo`. Ce dernier changement reste non commité
sur la branche de base.

Constaté le 2026-10-07 sur affut, après le redémarrage de 12:18 :

1. la fiche `ticket-004` remise en `todo` est restée modifiée sur `main` ;
2. au lancement de la file suivante, le commit de suivi l'a commitée sur
   `main` avant la création de la branche du ticket (commit
   « chore: tessera pipeline bookkeeping », un seul fichier) ;
3. le contrôle de divergence (`base_ref_divergee`,
   `backend/src/tessera/services/git_workspace.py`) a comparé `main` à
   `origin/main` et a bloqué le run, qui s'est arrêté sans créer sa branche.

Il a fallu un `git reset --keep origin/main` à la main.

## Solution proposée

Remettre la fiche en `todo` (dossier **et** champ) **sur la branche du
ticket, avant** le commit « unapproved work », pour qu'elle en fasse partie.
Revenir ensuite sur la branche de base sans y écrire quoi que ce soit : la
fiche y garde l'état qu'elle a sur la base.

Les autres comportements du ticket-369 ne changent pas (staging des seuls
fichiers suivis, aucune action si la copie de travail est sur une autre
branche, erreurs journalisées sans lever).

## Critères d'acceptation

- [ ] Un test de `backend/tests/test_reprise_run_orphelin.py` vérifie qu'après la reprise, la branche de base pointe sur le même commit qu'avant la reprise
- [ ] Un test de `backend/tests/test_reprise_run_orphelin.py` vérifie qu'après la reprise, `git status --porcelain --untracked-files=no` est vide sur la branche de base
- [ ] Un test de `backend/tests/test_reprise_run_orphelin.py` vérifie que le commit « unapproved work » de la branche du ticket contient la fiche du ticket dans `tickets/todo/` avec `status: todo`
- [ ] Un test de `backend/tests/test_reprise_run_orphelin.py` vérifie qu'un run lancé après la reprise ne lève pas de divergence de base : la branche de base locale n'a aucun commit absent de son amont simulé
- [ ] Les tests existants de `backend/tests/test_reprise_run_orphelin.py` passent toujours

## Dépendances

Aucune.

## Estimation

0,5 jour.

## Risques

Aucun pour la branche de base, qui n'est plus touchée.

## Ce que ça ne fait pas

- Ne change pas le contrôle de divergence : une base qui a vraiment divergé
  doit toujours bloquer.