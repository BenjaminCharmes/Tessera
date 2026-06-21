---
id: ticket-022
title: "API CRUD agents dynamiques"
type: feat
status: done
priority: high
agent: codeur
depends_on:
  - ticket-021
estimated_days: 0.5
created: 2026-06-21
---

# ticket-022 — API CRUD agents dynamiques

## Objectif

Exposer le registre d'agents (ticket-021) via une API REST, afin que l'UI et des outils externes puissent lister, consulter, créer et supprimer des agents sans accès direct au filesystem.

## Contexte

Après ticket-021, `AgentRegistryService` existait mais n'était accessible que via le code Python. Ce ticket a créé l'API REST sécurisée.

## Solution implémentée

Router `backend/src/vibe_ide/routers/agent_admin.py` monté sur `/api/v1/agents/registry`.

| Méthode | Path | Status |
|---|---|---|
| `GET` | `/agents/registry` | ✅ |
| `GET` | `/agents/registry/{role}` | ✅ |
| `POST` | `/agents/registry` | ✅ |
| `DELETE` | `/agents/registry/{role}` | ✅ 403 sur built-in |

## Critères d'acceptation

- [x] `GET /agents/registry` retourne la liste complète avec badge built-in/custom
- [x] `POST /agents/registry` crée un fichier prompt et retourne `201`
- [x] `DELETE /agents/registry/{role}` sur un built-in retourne `403`
- [x] Un `role` malformé (`../secrets`, `foo bar`) retourne `422` avant toute I/O

## Dépendances

- **ticket-021** — `AgentRegistryService` pour les opérations CRUD.

## Estimation

**0.5j** (réalisé)
