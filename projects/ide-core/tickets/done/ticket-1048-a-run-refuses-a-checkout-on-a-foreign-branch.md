---
agent: codeur
created: 2026-11-23
depends_on: []
estimated_days: 1
id: ticket-1048
plan: true
pr_number: 1253
priority: high
status: done
title: A run refuses a checkout left on a foreign branch, and reads its policy after
  realigning the base
type: fix
---

# ticket-1048 — Un run refuse un checkout laissé sur une branche étrangère, et lit sa politique après le réalignement de la base

## Objectif

Qu'un run d'un projet sans worktree ne parte pas quand son checkout est sur la
branche d'un autre travail, et qu'il ne décide jamais d'après un `agents.json`
plus vieux que la base dont il part.

## Contexte

Le 23/11 à 15:25 UTC, le run du ticket-1044 d'ide-core a été lancé alors que le
checkout était sur `ticket-rituels-23-11-tickets`, branche d'une autre session,
en retard d'un commit sur `develop`. Rien ne l'a refusé :

- `_realigner_base_au_depart` (`services/pipeline/pipeline_branche.py`) remet
  l'arbre sur la base quand il est « resté sur la branche du ticket précédent »
  (ticket-457), sans distinguer cette branche d'une branche étrangère ;
- la politique du run (`PolitiqueRun.lire`, dans `routers/orchestrator.py` et
  `services/pipeline/assemblage_run.py`) est lue **avant** ce réalignement,
  donc sur l'arbre de la branche étrangère.

Conséquence constatée : `base_branch`, ajouté à `agents.json` par un commit
que la branche étrangère n'avait pas, a été ignoré pendant tout le run, et la
documentation a encore reçu le diff contre le `main` local (2 847 fichiers au
lieu de 8). Le checkout aurait aussi pu porter le travail non poussé d'un
autre : il était propre, par chance.

## Solution proposée

1. À l'ouverture d'un run ou d'une file sur un projet **sans** worktree, si la
   branche courante n'est ni la base du projet ni la branche d'un ticket de ce
   projet (`ticket-<numéro>-…` dont le ticket existe sous `tickets/`), la
   requête est refusée avec un message qui nomme la branche et dit quoi faire.
   Pas de bascule silencieuse.
2. La politique du run est relue après le réalignement de la base, avant le
   premier agent : un réglage arrivé par la base est celui du run.
3. Les projets à worktree ne changent pas : leur run ne touche pas au checkout.

## Critères d'acceptation

- [ ] Un test d'ouverture de run, sur un projet sans worktree dont le checkout
      est sur une branche `autre-travail`, obtient un refus dont le message
      nomme `autre-travail`, et aucune branche n'est créée.
- [ ] Un test vérifie qu'un checkout resté sur la branche d'un ticket existant
      du projet démarre toujours (comportement du ticket-457 conservé).
- [ ] Un test vérifie qu'un `agents.json` modifié sur la base distante, absent
      de l'arbre au lancement, est celui que le run applique après
      réalignement (par exemple `base_branch`).
- [ ] Un test vérifie qu'un projet à worktree n'est pas refusé quand son
      checkout est sur une autre branche.

## Ce que ça ne fait pas

- N'empêche pas une session de changer la branche du checkout pendant un run :
  la consigne reste le worktree manuel.
- Ne touche pas au cas d'un arbre sale, déjà refusé.

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

Une file qui enchaîne ses tickets repart parfois de la branche du ticket
précédent : le deuxième critère protège ce cas, à ne pas casser.