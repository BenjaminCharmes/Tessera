---
id: ticket-1026
title: "The tickets a design run writes are committed with it and reach the validator"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-11-19
---

# ticket-1026 — Les tickets écrits par un run de conception se commitent avec lui et arrivent au validateur

## Signalement

Deux runs de conception du 19/11 :

- ticket-1016 : `validateur: fichiers cités joints : memory/decisions.md
  (tronqué) ; non joints (budget épuisé) : tickets/todo/`, approuvé quand
  même ; puis `fichiers non suivis laissés par le run :
  tickets/todo/ticket-1018-…, ticket-1019-…, ticket-1020-…, ticket-1021-…`.
- ticket-944 : même première ligne, mais `CHANGES_REQUESTED` trois tours de
  suite, puis `BLOCKED`. Les deux fiches écrites par l'architecte
  (1023, 1024) sont restées non suivies dans le checkout, laissé sur la
  branche du run. La décision était bonne ; il a fallu la livrer à la main.

## Contexte

Un ticket `design` produit une ADR et des fiches dans `tickets/todo/`. Son
critère type dit « chaque décision a un ticket dans `tickets/todo/` ».

- Le validateur ne reçoit pas ces fiches : le dossier cité entre backticks
  dépasse le budget des fichiers joints
  (`services/verdicts/validator_cited_files.py`), alors que les fiches
  nouvelles ne sont pas dans le diff qu'il lit, faute d'être suivies par git.
- À la fin du run, `services/pipeline/pipeline_fin_de_file.py` signale ces
  fichiers comme « non suivis laissés par le run » au lieu de les tenir pour
  le livrable.

## Ce qu'il faut faire

- Les fichiers créés par le run sous `tickets/todo/` du projet entrent dans
  le commit du run, approuvé ou non, comme le reste de son travail.
- Ils entrent dans le diff remis au reviewer et au validateur (fichiers
  ajoutés, contenu entier).
- Le message « fichiers non suivis laissés par le run » ne les cite plus.

## Critères d'acceptation

- [ ] Test (dépôt réel) : un run qui crée
  `tickets/todo/ticket-900-x.md` le retrouve dans son commit de fin, approuvé
  comme non approuvé.
- [ ] Test : le diff remis au validateur contient le contenu d'une fiche
  créée sous `tickets/todo/` pendant le run.
- [ ] Test : un fichier non suivi créé ailleurs que sous `tickets/todo/`
  reste signalé comme aujourd'hui.

## Ce que ça ne fait pas

- Ne change pas le budget des fichiers cités joints au validateur.
- Ne commite aucun autre fichier non suivi.
