---
id: ticket-871
title: "Activate the supervisor on ide-core, without delegation, at 2 USD a day"
type: chore
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 0.1
created: 2026-11-06
---

# ticket-871 — Activer le superviseur sur ide-core

## Objectif

Mettre en marche le superviseur (ADR-080) sur ide-core seulement, pour une
semaine d'observation, sans qu'il décide d'aucune leçon ni règle.

## Contexte

Les tickets 848 à 867 l'ont livré, mais aucun projet ne déclarait le rôle :
la boucle tournait à vide. Décision de Benjamin le 06/11 : ide-core seulement,
sans délégation des règles et leçons pendant une semaine.

## Solution proposée

Fait **à la main** : `agents.json` et `CLAUDE.md` sont fermés aux agents
(ADR-027, `chemins_proteges.py`).

- `agents.json` : rôle `superviseur` actif, `claude-sonnet-5-5`, `agent_sdk` ;
  `pipeline.superviseur` = `budget_jour_usd: 2.0`, `delegation: []`,
  `relance_file: false`.
- **Ce ticket autorise la modification de `projects/ide-core/CLAUDE.md`**
  (règle 5) : une ligne `superviseur` dans « Agents actifs sur ce projet »,
  que `test_consignes_coherentes.py` confronte à `agents.json`.

## Critères d'acceptation

- [x] `projects/ide-core/agents.json` déclare le rôle `superviseur` actif.
- [x] `pipeline.superviseur` porte `budget_jour_usd: 2.0` et `delegation: []`.
- [x] `projects/ide-core/CLAUDE.md` nomme `superviseur` dans ses agents actifs.

## Dépendances

Tickets 848 à 867 (mergés).

## Estimation

Une heure.

## Risques

Budget : 2 $/jour au plus, plafond vérifié par `ConfigSuperviseur`.

## Ce que ça ne fait pas

Ni délégation des leçons et règles, ni relance de file coupée : à revoir
après une semaine, vers le 13/11, sur le récapitulatif du superviseur.
