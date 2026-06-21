---
id: ticket-033
title: "Création automatique des agents manquants à la création de projet"
type: feat
status: todo
priority: medium
agent: codeur
depends_on:
  - ticket-023
  - ticket-024
estimated_days: 1
created: 2026-06-21
---

# ticket-033 — Création automatique des agents manquants

## Objectif

Éliminer la friction résiduelle lors de la création d'un projet : si `project-creator` suggère un agent absent du registre, celui-ci est créé **automatiquement et silencieusement** sans que l'utilisateur ait à faire une étape supplémentaire.

## Contexte

Avec ticket-023 (agent-creator) et ticket-024 (UI agents), la création d'agents manquants est possible mais manuelle : l'utilisateur voit un avertissement "L'agent `redacteur` n'existe pas" et doit cliquer pour le créer. Ce ticket rend ce flow entièrement automatique — l'utilisateur crée son projet et le trouve opérationnel.

### Flux actuel (friction)
```
project-creator → suggested_agents: ["codeur", "redacteur"]
"redacteur" absent → ⚠ lien "Créer l'agent"   ← blocage UX
```

### Flux après ticket-033
```
project-creator → suggested_agents: ["codeur", "redacteur"]
"redacteur" absent → agent-creator invoqué automatiquement
                   → system prompt généré en tâche de fond
                   → agent créé silencieusement
Projet prêt avec tous ses agents ✅
```

## Solution proposée

### `ProjectCreatorService.create_project()` — enrichissement

Après extraction du JSON et avant retour de la réponse, vérifier chaque agent suggéré :

```python
agents_created: list[str] = []
for agent_role in result.active_agents:
    if not registry.exists(agent_role):
        prompt = await self._bootstrap_agent(agent_role, result)
        registry.create_agent(agent_role, prompt)
        agents_created.append(agent_role)

return CreateProjectResponse(..., agents_created=agents_created)
```

### `ProjectCreatorService._bootstrap_agent()` (nouveau)

Appel Claude direct (non conversationnel) :
```
Génère le system prompt d'un agent nommé "{role}" pour le projet "{name}".
Description du projet : {description}
Réponds uniquement avec le system prompt (min 50 mots), sans JSON.
```

### `CreateProjectResponse` — nouveau champ

```python
class CreateProjectResponse(BaseModel):
    ...
    agents_created: list[str] = []  # agents auto-créés
```

### Frontend — `CreateProjectModal`

Afficher les agents auto-créés dans le message de succès :
```
✅ Projet "Mon Roman" créé
   2 agents créés automatiquement : redacteur, planificateur
```

### `ImportProjectModal` (ticket-027) — simplification

Retirer le lien manuel "Créer l'agent manquant" → remplacer par message informatif.

## Critères d'acceptation

- [ ] Un projet avec un agent absent (`redacteur`) est créé sans étape supplémentaire pour l'utilisateur
- [ ] Les agents auto-créés sont listés dans le message de succès
- [ ] Un projet dont tous les agents existent → `agents_created: []` (aucune latence supplémentaire)
- [ ] L'`ImportProjectModal` affiche un message informatif au lieu d'un lien d'action

## Spécifications techniques

`_bootstrap_agent()` est distinct de `AgentCreatorService` : pas de conversation, génération directe, rapide. Modèle Haiku 4.5 (coût faible, invoqué pour chaque agent manquant).

En cas d'échec de `_bootstrap_agent()` : logger l'erreur et continuer sans bloquer la création du projet. L'utilisateur peut créer l'agent manuellement ensuite.

## Dépendances

- **ticket-023** — `AgentRegistryService` pour vérifier et créer les agents.
- **ticket-024** — `CreateProjectModal` pour afficher les agents auto-créés.

## Estimation

**1j** — Extension du service existant + tests + frontend.

## Risques

- **Faible** — La génération auto peut produire des prompts de qualité variable. Le système reste fonctionnel — l'utilisateur peut éditer le prompt ensuite.
