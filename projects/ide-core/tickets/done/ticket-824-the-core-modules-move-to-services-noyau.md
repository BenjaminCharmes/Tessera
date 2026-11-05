---
id: ticket-824
title: "The core modules move to services/noyau"
type: refactor
status: done
pr_number: null
priority: low
agent: codeur
depends_on: [ticket-823]
estimated_days: 1
created: 2026-11-05
---

# ticket-824 — Les modules du noyau passent dans `services/noyau/`

## Objectif

Les vingt-cinq modules du domaine `noyau` (base, événements, journaux, processus, texte et diff)
vivent dans `services/noyau/`, à comportement constant.

## Contexte

ADR-076 ; section `noyau` de `memory/services-domaines.md`. Dernier domaine : tout le reste en
importe, ce déplacement touche le plus de fichiers, d'où le calendrier. Ce qui reste à plat après lui
est vide.

## Ce que le ticket fait

- Lance `scripts/deplacer_domaine.py noyau`, relit le diff, lance la suite.
- Vérifie `scripts/prochain_numero.py` (`numerotation`) et `backend/tests/conftest.py`
  (`event_hub`, `database`).

## Critères d'acceptation

- [x] Les vingt-cinq modules de la section `noyau` sont sous `services/noyau/`, aucun n'est resté
      à plat
- [x] `A_DEPLACER` est vide, `ECARTS_DOMAINES` n'a grandi d'aucune ligne
- [x] `python scripts/prochain_numero.py ticket` répond toujours
- [x] Aucune occurrence des anciens chemins pointés ne reste dans `backend/src`, `backend/tests`,
      `scripts/`, `Makefile`
- [x] Le diff n'est que des renommages et des lignes d'import ou de chaîne ; la suite passe

## Ce que ça ne fait pas

Aucun changement de comportement. Le test ne refuse pas encore les modules à plat : c'est le
ticket-825.

## Risques

`prochain_numero.py` est lancé par les agents Architect pour numéroter : le casser les prive de
leur numéro. Le lancer une fois avant la PR.

## Notes de réalisation

Le domaine compte vingt-deux modules, pas vingt-cinq : `scripts/domaines_services.py` fait foi (dont `cost_calculator`, reclassé ici au ticket-826). `scripts/prochain_numero.py` (`numerotation`), `scripts/mesure_calculs.py` (`cost_calculator`) et `backend/tests/conftest.py` (`event_hub`, `database`) sont réécrits par le script ; `prochain_numero.py ticket` répond. `test_modeles_par_defaut.py` compare des noms de fichiers : inchangé. `orchestrator.py` reste à 627 lignes. `docs/architecture.md` suit `lancement` et `database`. Suite backend complète : 5320 passed.
