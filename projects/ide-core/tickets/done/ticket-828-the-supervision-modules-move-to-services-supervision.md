---
id: ticket-828
title: "The supervision modules move to services/supervision"
type: refactor
status: done
pr_number: null
priority: low
agent: codeur
depends_on: [ticket-827]
estimated_days: 1
created: 2026-11-05
---

# ticket-828 — Les modules de supervision passent dans `services/supervision/`

## Objectif

Les quatorze modules du domaine `supervision` (processus, services, apps, salles) vivent dans
`services/supervision/`, à comportement constant.

## Contexte

ADR-076 ; liste du domaine dans `memory/services-domaines.md`, section `supervision`. Premier
déplacement : c'est le domaine que le moins de fichiers importent, il éprouve le script (ticket-827).

## Ce que le ticket fait

- Lance `scripts/deplacer_domaine.py supervision`, relit le diff, lance la suite.
- Rien d'autre : ni renommage de fonction, ni nettoyage, ni reclassement hors de la table.

## Critères d'acceptation

- [x] Les quatorze modules de la section `supervision` sont sous `services/supervision/`, aucun
      n'est resté à plat
- [x] `A_DEPLACER` n'a plus d'entrée `supervision`, `ECARTS_DOMAINES` n'a grandi d'aucune ligne
- [x] Aucune occurrence des anciens chemins pointés (`tessera.services.<module>`) ne reste dans
      `backend/src`, `backend/tests`, `scripts/`, `Makefile`
- [x] Le diff n'est que des renommages et des lignes d'import ou de chaîne ; la suite passe

## Ce que ça ne fait pas

Aucun changement de comportement. Les autres domaines ne bougent pas.

## Risques

Une chaîne de `monkeypatch` non réécrite ne casse pas à l'import : la rechercher par
`grep "tessera.services.<module>"` après le script, pour chaque module déplacé.

## Notes de réalisation

Le domaine compte onze modules, pas quatorze : `scripts/domaines_services.py` fait foi (trois modules reclassés au ticket-826). Les anciens chemins cités dans `docs/audit/`, `docs/superpowers/specs/` et les tickets terminés restent tels quels : ils datent l'état décrit.
