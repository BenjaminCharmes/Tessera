---
agent: codeur
created: '2026-11-16'
depends_on: []
id: ticket-985
priority: medium
status: todo
title: Un ticket arrêté porte toujours son motif
type: fix
---

## Signalement

- Projet source : carriere (session Carrière, 16/11 ; aussi déposé par
  `POST /signalements`, en attente : le ticket qu'il produira est un doublon
  de celui-ci, à passer en `cancelled`)
- Nature : bug

## Contexte

Carrière, runs `3f106a12` et `317e64bd`, 16/11 : le ticket-090 s'arrête en
`security_block` (audit indisponible faute de quota, porte fermée comme
prévu). `GET /api/v1/runs/<id>` le range bien dans `arretes`, mais avec
`motif: null`, alors que l'événement `pipeline_done` porte
`reason: "security_block"`. Une session qui lit l'état d'une file ne sait
pas pourquoi le ticket s'est arrêté sans relire les événements.

`faits` qui contient aussi ce ticket n'est pas un défaut : depuis le
ticket-444, `faits` est déprécié et vaut `approuves` + `arretes`.

Cause : `run_status.classer_les_tickets` lit le motif dans la colonne
`arret` de `pipeline_runs`, remplie depuis `PipelineResult.arret`. Or
plusieurs fins de `services/pipeline/pipeline_outcomes.py` ne renseignent
`arret` qu'en cas d'échec du commit : `finish_security_block` (le résumé de
l'audit est perdu), `finish_stopped`, `finish_rounds_exhausted`, et
peut-être d'autres.

## Ce qu'il faut faire

Chaque fin non approuvée de `pipeline_outcomes.py` renseigne
`PipelineResult.arret` avec un motif court et lisible, sans écraser un
`arret` d'échec de commit déjà présent (celui-ci prime, il dit pourquoi
l'arbre n'est pas propre) :

- `finish_security_block` : `audit sécurité : <première ligne du résumé>` ;
- `finish_stopped` : `arrêté à la demande` ;
- `finish_rounds_exhausted` : `non approuvé après <N> tours` ;
- toute autre fin non approuvée qui n'en a pas : son code de `reason`.

## Critères d'acceptation

- [ ] Test : `finish_security_block` rend un `PipelineResult` dont `arret`
      commence par `audit sécurité : ` et contient la première ligne du
      résumé.
- [ ] Test : quand le commit échoue, `arret` reste le motif d'échec du
      commit.
- [ ] Test : `finish_stopped` et `finish_rounds_exhausted` rendent un
      `arret` non vide.
- [ ] Test : un test paramétré sur toutes les fonctions `finish_*` non
      approuvées de `pipeline_outcomes.py` vérifie que `arret` n'est jamais
      vide.
- [ ] Test : `classer_les_tickets` donne un `motif` non nul pour une ligne
      `security_block` enregistrée avec ce nouvel `arret`.

## Ce que ça ne fait pas

- Ne retire pas `faits` (déprécié par le ticket-444, gardé pour les
  clients existants).
- Ne réécrit pas les lignes déjà enregistrées en base.
