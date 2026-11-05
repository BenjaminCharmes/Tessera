---
id: ticket-817
title: "The project modules move to services/projets"
type: refactor
status: todo
pr_number: null
priority: low
agent: codeur
depends_on: [ticket-816]
estimated_days: 1
created: 2026-11-05
---

# ticket-817 — Les modules de projet passent dans `services/projets/`

## Objectif

Les onze modules du domaine `projets` (manifeste, tickets, ADR, artefacts, autonomie, déclaration
de mise en ligne) vivent dans `services/projets/`, à comportement constant.

## Contexte

ADR-074 ; section `projets` de `memory/services-domaines.md`. `manifeste` est le lecteur unique de
`agents.json` (ADR-068) et `project_loader` est importé presque partout : ce déplacement réécrit le
plus de lignes d'import, d'où sa place tardive. Le dossier et le module `manifeste` ne se
confondent pas (`projets` / `manifeste`).

## Ce que le ticket fait

- Lance `scripts/deplacer_domaine.py projets`, relit le diff, lance la suite.
- Réécrit `Makefile` et `scripts/tessera.ps1`, qui lancent `python -m tessera.services.ticket_check`
  (désormais `tessera.services.projets.ticket_check`), et vérifie que la commande répond.
- Vérifie `scripts/prochain_numero.py` : il importe `numerotation`, qui bougera au ticket-818.

## Critères d'acceptation

- [ ] Les onze modules de la section `projets` sont sous `services/projets/`, aucun n'est resté à plat
- [ ] `make` (cible de vérification des tickets) et `scripts/tessera.ps1` appellent le nouveau chemin
- [ ] `A_DEPLACER` n'a plus d'entrée `projets`, `ECARTS_DOMAINES` n'a grandi d'aucune ligne
- [ ] Aucune occurrence des anciens chemins pointés ne reste dans `backend/src`, `backend/tests`,
      `scripts/`, `Makefile`
- [ ] Le diff n'est que des renommages et des lignes d'import ou de chaîne ; la suite passe

## Ce que ça ne fait pas

Aucun changement de comportement, aucune lecture de manifeste modifiée.

## Risques

`project_loader` est patché par chaîne dans les tests de routeurs : relire les restes de chemins.
