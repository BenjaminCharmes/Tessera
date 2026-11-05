---
id: ticket-815
title: "The verification modules move to services/verification"
type: refactor
status: todo
pr_number: null
priority: low
agent: codeur
depends_on: [ticket-814]
estimated_days: 1
created: 2026-11-05
---

# ticket-815 — Les modules de vérification passent dans `services/verification/`

## Objectif

Les quinze modules du domaine `verification` (lancer les tests, contrôle visuel, captures) vivent
dans `services/verification/`, à comportement constant.

## Contexte

ADR-076 ; section `verification` de `memory/services-domaines.md`. Le ticket-773 (ruff dans la
commande de test) touche cette zone : sa PR est mergée avant ce ticket.

## Ce que le ticket fait

- Lance `scripts/deplacer_domaine.py verification`, relit le diff, lance la suite.
- Corrige à la main `captures.py` : `Path(__file__).resolve().parents[4]` devient `parents[5]`, et
  un test prouve que le script `scripts/captures.mjs` est bien retrouvé.
- Relit `scripts/captures.mjs` (commentaire qui cite `services/captures.py`) et le met à jour.

## Critères d'acceptation

- [ ] Les quinze modules de la section `verification` sont sous `services/verification/`, aucun
      n'est resté à plat
- [ ] `captures._SCRIPT` désigne `scripts/captures.mjs`, un test le vérifie
- [ ] `A_DEPLACER` n'a plus d'entrée `verification`, `ECARTS_DOMAINES` n'a grandi d'aucune ligne
- [ ] Aucune occurrence des anciens chemins pointés ne reste dans `backend/src`, `backend/tests`,
      `scripts/`, `Makefile`
- [ ] Le diff n'est que des renommages, des lignes d'import ou de chaîne, et la correction de
      `parents[N]` ; la suite passe

## Ce que ça ne fait pas

Aucun changement de comportement du lancement des tests ni des captures.

## Risques

Un chemin trop haut ou trop bas pour `captures.mjs` ne casse rien avant la première capture : d'où
le test sur le chemin.
