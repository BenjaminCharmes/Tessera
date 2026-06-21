---
id: ticket-021
title: "Registre d'agents dynamiques (backend, fondation)"
type: refactor
status: done
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-06-21
---

# ticket-021 — Registre d'agents dynamiques

## Objectif

Permettre la création et l'utilisation d'agents personnalisés sans avoir à modifier le code source. Aujourd'hui, ajouter un rôle (`redacteur`, `data-analyst`) provoque un crash Pydantic. Ce ticket pose la fondation qui rend le système extensible.

## Contexte

Les agents étaient définis par un enum fermé `AgentRole` dans `models/agent.py`. Si `project-creator` suggérait un agent absent de cet enum, le pipeline plantait à la validation Pydantic — aucun moyen d'étendre dynamiquement la liste.

Architecture cible : chaque agent = un fichier `agents/prompts/{role}.md`. Un `AgentRegistryService` scanne ce dossier et expose le CRUD. Les 6 agents built-in conservent leur prompt existant ; les agents custom sont créés/supprimés à la volée.

## Solution implémentée

1. **`backend/src/vibe_ide/services/agent_registry.py`** — `AgentRegistryService` avec CRUD + `AgentNotFoundError`
2. **`models/agent.py`** — `AgentResult.role` et `AgentRunRequest.role` : `AgentRole` → `str`
3. **`services/agent_runner.py`** — injection du registre, résolution via `registry.get_prompt(role)`
4. **`utils/json_extract.py`** — utilitaire partagé extrait depuis `project_creator.py`

## Critères d'acceptation

- [x] Un agent créé via fichier `.md` est utilisable dans un pipeline sans modifier le code
- [x] Un rôle inconnu déclenche `AgentNotFoundError` et non un crash Pydantic
- [x] Les 6 agents built-in continuent de fonctionner exactement comme avant
- [x] Les tests existants (`test_orchestrator.py`, `test_github_service.py`) restent verts

## Dépendances

Aucune. Pré-requis de tous les tickets agents (022, 023, 026, 028, 034-037).

## Estimation

**1j** (réalisé)

## Risques

**Moyen** — Résolu : tests de non-régression écrits avant le refactor.
