---
agent: codeur
created: 2026-11-06
depends_on: []
estimated_days: 0.5
id: ticket-876
pr_number: 971
priority: medium
status: done
title: The AgentRole enum only names roles the registry knows, checked by a test
type: refactor
---

# ticket-876 — `AgentRole` ne nomme que des rôles du registre

## Objectif

L'enum `AgentRole` ne peut plus diverger du registre d'agents : un test le
confronte à `BUILTIN_ROLES`.

## Contexte

Audit externe du 06/11 (« rôles définis à cinq endroits »), vérifié : la
source réelle est `backend/src/tessera/services/agents/agent_registry.py`
(`BUILTIN_ROLES`, `ROLES_PIPELINE`, `ROLES_A_LA_DEMANDE`), déjà confrontée
aux prompts par un test. Mais `AgentRole`
(`backend/src/tessera/models/agent.py`) est un sous-ensemble périmé qui
porte `orchestrateur`, un rôle sans prompt, et
`backend/src/tessera/services/agents/agent_runner.py` lui associe encore des
outils. `github-sync` y est légitime : c'est un rôle de service, exclu du
registre exprès.

Le nom de poste `resolveur` du Bureau (frontend) est un nom d'affichage : hors
périmètre.

## Solution proposée

- Retirer `orchestrateur` d'`AgentRole` et son entrée dans `agent_runner.py`,
  après avoir vérifié qu'aucun appel ne l'utilise.
- Un test : chaque valeur d'`AgentRole` est dans `BUILTIN_ROLES` ou vaut
  `github-sync`.

## Critères d'acceptation

- [ ] `backend/src/tessera/models/agent.py` ne déclare plus
      `orchestrateur` dans `AgentRole`.
- [ ] `backend/src/tessera/services/agents/agent_runner.py` n'a plus d'entrée
      pour `orchestrateur`.
- [ ] Un test de `backend/tests/test_agent_role_registre.py` échoue si une
      valeur d'`AgentRole` n'est ni dans `BUILTIN_ROLES` ni `github-sync`.

## Dépendances

Aucune.

## Estimation

Une demi-journée.

## Risques

Un `agents.json` de projet qui déclarerait `orchestrateur` : le codeur le
cherche dans `projects/*/agents.json` avant de retirer la valeur.