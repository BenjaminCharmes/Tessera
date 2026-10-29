---
agent: codeur
created: '2026-10-22'
depends_on: []
id: ticket-539
priority: medium
status: done
title: Un push refusé en « reference already exists » alors que la branche est déjà
  poussée laisse le run done sans PR
type: fix
---

## Signalement

- Projet source : kadoomi
- Nature : bug
- Reçu le : 2026-10-22

## Description

Run b1b866cc (kadoomi, ticket-098), 22/10 16:14 UTC. pipeline_done approuvé (ff8ae22). La branche ticket-098-… est bien arrivée sur origin à 644fc46 (16:14:40, commit bookkeeping compris), mais livraison_done rapporte « Livraison interrompue : GitCommandError … push --set-upstream origin ticket-098-… ! [remote rejected] … cannot lock ref … reference already exists ». Aucune PR n’est ouverte (pr_number null), pr_orpheline false, et run_closed final_status done. Un commit local de bookkeeping (eb7d96d, +1 ligne de pipeline-log) n’est jamais poussé. Le ticket se retrouve done sans PR ni merge, sans rien qui le signale.

## Contexte

Piste : un push qui échoue alors que la branche distante pointe déjà sur un ancêtre ou sur le commit attendu devrait être traité comme réussi (relire la ref distante), puis ouvrir la PR. Et une livraison interrompue ne devrait pas fermer le run en done silencieusement. Contournement : PR ouverte à la main depuis la branche distante.

## Critères d'acceptation

- [x] Un push refusé alors que `origin/<branche>` est déjà sur la tête locale compte comme réussi : la PR s'ouvre
- [x] Un push refusé alors que le distant est un ancêtre de la tête locale est rejoué une fois, sans force
- [x] Un distant divergé ou absent garde le refus d'origine, et rien n'est forcé

## Ce que ça ne fait pas

- Une livraison interrompue ferme toujours le run en `done`, `Livraison.arret` portant le motif : ADR-030 le décide ainsi, le changer demande sa propre décision.