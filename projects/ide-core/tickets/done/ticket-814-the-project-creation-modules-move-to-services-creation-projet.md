---
id: ticket-814
title: "The project creation modules move to services/creation_projet"
type: refactor
status: done
pr_number: null
priority: low
agent: codeur
depends_on: [ticket-813]
estimated_days: 1
created: 2026-11-05
---

# ticket-814 — Les modules de création de projet passent dans `services/creation_projet/`

## Objectif

Les dix modules du domaine `creation_projet` (créer, importer, cloner, retirer un projet) vivent
dans `services/creation_projet/`, à comportement constant.

## Contexte

ADR-076 ; section `creation_projet` de `memory/services-domaines.md`. Le ticket-758 (durcissement
des URL de clone) touche `git_clone` : il passe avant ce ticket, ou sa PR est mergée avant lui.

## Ce que le ticket fait

- Lance `scripts/deplacer_domaine.py creation_projet`, relit le diff, lance la suite.

## Critères d'acceptation

- [x] Les dix modules de la section `creation_projet` sont sous `services/creation_projet/`, aucun
      n'est resté à plat
- [x] `A_DEPLACER` n'a plus d'entrée `creation_projet`, `ECARTS_DOMAINES` n'a grandi d'aucune ligne
- [x] Aucune occurrence des anciens chemins pointés ne reste dans `backend/src`, `backend/tests`,
      `scripts/`, `Makefile`
- [x] Le diff n'est que des renommages et des lignes d'import ou de chaîne ; la suite passe

## Ce que ça ne fait pas

Aucun changement de comportement, aucun gabarit de projet modifié.

## Risques

`gabarits_projet` et `template_claude_md` lisent peut-être des fichiers relatifs à leur emplacement :
le script signale tout `__file__` ; le corriger à la main s'il y en a.

## Notes de réalisation

Le domaine compte huit modules, pas dix : `scripts/domaines_services.py` fait foi. Les chaînes de `monkeypatch` (`git_clone`, `project_from_template`) sont réécrites. Seuls des documents historiques citent les anciens chemins : ils restent tels quels.
