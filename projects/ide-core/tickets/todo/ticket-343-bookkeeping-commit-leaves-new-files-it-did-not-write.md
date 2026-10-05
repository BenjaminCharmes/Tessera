---
id: ticket-343
title: "The bookkeeping commit leaves out ticket files created during the run that Tessera did not move"
type: fix
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-05
---

# ticket-343 — Le commit de suivi n'embarque plus un ticket écrit pendant le run

## Objectif

Le commit de suivi d'un run ne contient que ce que Tessera a écrit : le
déplacement du ticket du run et `memory/pipeline-log.md`, jamais un ticket
posé à côté pendant que le run tournait.

## Contexte

`commit_bookkeeping` (`backend/src/tessera/services/git_workspace.py`) stage
`tickets/` en entier (`_ORCHESTRATOR_ARTIFACT_PATHS`), moins les fichiers non
suivis **au démarrage** du run (`_preexisting_untracked`, relevé dans
`create_branch`). Un fichier créé sous `tickets/` *pendant* le run n'est dans
aucune des deux listes : il part dans le commit de suivi.

Le 2026-10-05, deux tickets du projet `carriere` (062 et 063), écrits dans
`tickets/todo/` pendant le run du ticket-057, ont ainsi été commités sous
« chore: tessera pipeline bookkeeping », poussés sur la branche du 057 et
mergés avec sa PR. Rien de cassé ce jour-là, mais la PR d'un ticket porte des
fichiers qui n'ont rien à voir avec lui, et un ticket en cours de rédaction
peut partir à moitié écrit.

Ce que Tessera écrit réellement sous `tickets/` : il **déplace** un ticket
suivi d'un dossier de statut à l'autre et réécrit son frontmatter (statut,
`pr_number`). Un déplacement apparaît à git comme une suppression plus un
fichier non suivi **de même nom** dans un autre dossier.

## Solution proposée

1. `create_branch` relève aussi les noms de fichier (`basename`) des tickets
   **suivis** sous `tickets/` au démarrage du run.
2. `commit_bookkeeping` stage, sous `tickets/` :
   - les modifications et suppressions de fichiers suivis (inchangé) ;
   - un fichier non suivi **seulement** si son nom figure dans ce relevé
     (c'est un déplacement de statut).
   Tout autre fichier non suivi sous `tickets/` reste non suivi, dans l'arbre,
   intact.
3. `memory/pipeline-log.md` est stagé comme aujourd'hui.

## Critères d'acceptation

- [ ] Un test vérifie qu'un ticket suivi déplacé de `tickets/todo/` vers
      `tickets/done/` pendant le run figure dans le commit de suivi, à son
      nouveau chemin
- [ ] Un test vérifie qu'un fichier `tickets/todo/ticket-999-x.md` créé
      **après** `create_branch` ne figure pas dans le commit de suivi, et
      existe toujours, non suivi, dans l'arbre
- [ ] Un test vérifie qu'un fichier non suivi au démarrage du run reste exclu
      du commit de suivi (comportement de `_preexisting_untracked` conservé)
- [ ] `backend/tests/test_bookkeeping_apres_merge.py` passe sans modification
      de ses assertions existantes

## Ce que ça ne fait pas

- Ne touche pas au commit principal du run (`commit_all`) : un fichier créé
  par le codeur hors de `tickets/` est son travail, il doit y être.
- N'empêche pas d'écrire dans un projet pendant un run : ça évite seulement
  que ce qu'on y écrit parte avec le run.

## Dépendances

Aucune.

## Estimation

0,5 jour.

## Risques

Un ticket renommé par Tessera (slug changé) ne serait plus reconnu comme un
déplacement. Aucun code ne renomme un ticket aujourd'hui ; si ça change, le
relevé doit porter l'`id` du ticket plutôt que son nom de fichier.
