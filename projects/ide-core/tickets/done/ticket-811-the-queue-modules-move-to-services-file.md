---
id: ticket-811
title: "The queue modules move to services/file"
type: refactor
status: done
pr_number: null
priority: low
agent: codeur
depends_on: [ticket-829]
estimated_days: 1
created: 2026-11-05
---

# ticket-811 — Les modules de la file passent dans `services/file/`

## Objectif

Les sept modules du domaine `file` (file, mode autonome, planificateur) vivent dans
`services/file/`, à comportement constant.

## Contexte

ADR-076 ; section `file` de `memory/services-domaines.md`.

## Ce que le ticket fait

- Lance `scripts/deplacer_domaine.py file`, relit le diff, lance la suite.

## Critères d'acceptation

- [x] Les sept modules de la section `file` sont sous `services/file/`, aucun n'est resté à plat
- [x] `A_DEPLACER` n'a plus d'entrée `file`, `ECARTS_DOMAINES` n'a grandi d'aucune ligne
- [x] Aucune occurrence des anciens chemins pointés ne reste dans `backend/src`, `backend/tests`,
      `scripts/`, `Makefile`
- [x] Le diff n'est que des renommages et des lignes d'import ou de chaîne ; la suite passe

## Ce que ça ne fait pas

Aucun changement de comportement.

## Risques

Un nom de dossier `file` ressemble à un mot courant : chercher les chaînes par chemin pointé
complet, pas par `file`.

## Notes de réalisation

Le domaine compte cinq modules, pas sept : `scripts/domaines_services.py` fait foi. Seuls des documents historiques (tickets terminés, specs) citent les anciens chemins : ils restent tels quels.
