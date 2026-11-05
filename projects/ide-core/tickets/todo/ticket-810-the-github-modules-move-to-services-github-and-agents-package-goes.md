---
id: ticket-810
title: "The github modules move to services/github and the agents package goes"
type: refactor
status: todo
pr_number: null
priority: low
agent: codeur
depends_on: [ticket-809]
estimated_days: 1
created: 2026-11-05
---

# ticket-810 — Les modules GitHub passent dans `services/github/`, et `tessera/agents/` disparaît

## Objectif

Les huit modules du domaine `github` et `tessera/agents/github_sync.py` vivent dans
`services/github/`. Plus aucun paquet de premier niveau ne sort des couches.

## Contexte

ADR-074 ; section `github` de `memory/services-domaines.md`. `tessera/agents/` ne porte que
`github_sync.py`, qui importe `models` et `services` : il échappait au test d'architecture.
ADR-010 (`role: github-sync` géré dans `POST /api/v1/agents/run`) ne change pas.

## Ce que le ticket fait

- Lance `scripts/deplacer_domaine.py github`, relit le diff, lance la suite.
- Déplace `tessera/agents/github_sync.py` vers `services/github/github_sync.py`, réécrit ses
  importeurs (le routeur d'agents, les tests), supprime le dossier `tessera/agents/` et son
  `__init__.py`.
- Vide `PAQUETS_TOLERES` dans `backend/tests/test_domaines_services.py`.

## Critères d'acceptation

- [ ] Les huit modules de la section `github` et `github_sync` sont sous `services/github/`
- [ ] `backend/src/tessera/agents/` n'existe plus, `PAQUETS_TOLERES` est vide
- [ ] `A_DEPLACER` n'a plus d'entrée `github`, `ECARTS_DOMAINES` n'a grandi d'aucune ligne
- [ ] Aucune occurrence de `tessera.agents` ni des anciens chemins pointés ne reste dans
      `backend/src`, `backend/tests`, `scripts/`, `Makefile`
- [ ] Le diff n'est que des renommages, des lignes d'import ou de chaîne et la suppression du
      dossier vide ; la suite passe

## Ce que ça ne fait pas

Aucun changement de comportement de la synchronisation des issues.

## Risques

Le ticket-758 (jetons dans les URL, rapports bornés) touche `github_service` : sa PR est mergée avant.
