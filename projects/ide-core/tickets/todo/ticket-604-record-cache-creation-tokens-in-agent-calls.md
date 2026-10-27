---
id: ticket-604
title: "agent_calls records the cache creation tokens of each call"
type: chore
status: todo
priority: low
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-27
plan: true
---

# ticket-604 — agent_calls garde les tokens de création de cache

## Objectif
Que l'entrée réelle d'un rôle se lise dans `agent_calls`, sans sous-estimation.

## Contexte
ADR-059 reporte la compression du contexte faute de mesure.
`agent_sdk._usage_from` lit `cache_creation_input_tokens` et
`ProviderResult.cache_creation_tokens` le porte, mais la table `agent_calls` n'a
que `input_tokens` et `cache_read_tokens` : la valeur est jetée à l'écriture
dans `ProviderEnregistrant`.

## Solution proposée
Une colonne `cache_creation_tokens INTEGER NOT NULL DEFAULT 0`, ajoutée comme
les migrations existantes de `database.py` (liste d'`ALTER TABLE`), et écrite
par `record_agent_call` à chaque appel.

## Critères d'acceptation
- [ ] Une base créée avant ce ticket s'ouvre sans perte et reçoit la colonne, avec 0 pour les lignes existantes (test sur une base préparée sans la colonne)
- [ ] Un appel enregistré avec `cache_creation_tokens=7` laisse 7 dans `agent_calls` (test de `ProviderEnregistrant`)
- [ ] Les requêtes de coût et de statistiques existantes rendent les mêmes valeurs qu'avant

## Ce que ça ne fait pas
- N'ajoute pas la taille des segments du prompt.
- Ne change ni les prompts ni aucun affichage de l'interface.
