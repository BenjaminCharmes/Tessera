---
id: ticket-302
title: "A queue does not build the next ticket on an approved ticket whose merge failed"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
plan: true
created: 2026-10-02
---

# ticket-302 — Une file ne s'empile pas sur un ticket que la livraison n'a pas mergé

## Objectif

Qu'une CI rouge sur un ticket approuvé ne contamine pas les tickets suivants
de la même file.

## Contexte

Le 2026-10-01, la file ide-core a approuvé le 281, puis le 286, le 287, le 296
et le 297. Aucun n'a été mergé. Le 281 avait une erreur `eslint`, que ni le
testeur (suite backend seule) ni le reviewer ni le validateur ne voient. Sa
CI était rouge, et sa livraison a laissé la PR ouverte, comme prévu.

Mais `advance_base_ref` (`services/git_workspace.py`) fait avancer la base
dès l'approbation (ADR-018). Le ticket-285 ne réaligne la base sur le distant
qu'après un merge réussi. Les quatre tickets suivants ont donc forké de la
pointe du 281 : leurs PR contenaient ses commits, et elles ont toutes échoué
sur la même erreur `eslint`. Le 296 et le 297 ne touchaient pourtant que le
backend. Il a fallu corriger le 281, puis rebaser et merger les quatre autres
à la main, une par une, à cause du squash.

## Solution proposée

Sur un projet en `autonomy: merge`, quand la livraison d'un ticket approuvé
n'a **pas** mergé :

- le ticket suivant part de la base distante, alignée par
  `sync_base_depuis_distant`, et non de la pointe du ticket non mergé ;
- sauf s'il déclare ce ticket dans `depends_on`. Dans ce cas, la file
  s'arrête, avec un `arret` qui nomme la PR restée ouverte.

Le tour de plan vérifie comment cette règle s'articule avec le ticket-291
(démarrer le ticket suivant pendant la CI), qui touche au même endroit.

## Critères d'acceptation

- [ ] Un test vérifie qu'après un ticket approuvé dont la livraison rend
      `merged: false`, le ticket suivant crée sa branche depuis la base
      distante et non depuis la pointe du ticket précédent
- [ ] Un test vérifie qu'un ticket suivant qui déclare le précédent dans
      `depends_on` arrête la file, avec un `arret` qui contient le numéro de
      la PR ouverte
- [ ] Un test vérifie qu'après un merge réussi, le comportement du ticket-285
      est inchangé : le ticket suivant part du commit squashé
- [ ] Un test vérifie qu'un projet en `autonomy: commit` garde l'empilement
      actuel (ADR-018)

## Dépendances

Aucune. À relire avec le ticket-291.

## Estimation

1 jour.

## Risques

Sur un projet en `autonomy: commit` ou `pr`, rien ne merge jamais seul :
l'empilement y est voulu pour qu'un plan séquentiel avance. La règle ne vaut
que là où un merge était attendu et n'a pas eu lieu.
