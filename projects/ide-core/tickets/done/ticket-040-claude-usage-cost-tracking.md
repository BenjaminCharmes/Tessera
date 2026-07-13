---
id: ticket-040
title: "Suivi du coût et de l'usage des appels Claude"
type: feat
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1.5
created: 2026-07-11
---

# ticket-040 — Suivi du coût et de l'usage des appels Claude

## Objectif

Savoir combien coûte (en tokens et en $) le pipeline d'agents, par ticket et
globalement, pour piloter le budget d'usage de l'API Anthropic.

## Contexte

`AgentRunnerService` (`backend/src/vibe_ide/services/agent_runner.py:69-79`) logue déjà
`input_tokens`, `output_tokens` et `cache_read_tokens` par appel (log structuré
`"agent_call"`), mais :
- ces données ne sont pas persistées (perdues dès que les logs tournent)
- aucune conversion en coût $ (le prix dépend du modèle utilisé)
- aucune agrégation par ticket, par projet ou globale
- rien n'est visible dans l'UI — il faut aller lire les logs backend

## Solution proposée

### Persistence

Étendre le stockage SQLite existant (utilisé pour l'historique des pipelines,
`ticket-015`) avec une table `agent_calls` (ou équivalent) qui capture par appel :
`ticket_id`, `role`, `model`, `input_tokens`, `output_tokens`, `cache_read_tokens`,
`cost_usd`, `duration_ms`, `created_at`.

### Calcul du coût

Table de prix par modèle (input/output/cache-read $ par million de tokens),
appliquée sur les tokens de chaque appel pour calculer `cost_usd`. Prévoir un
endroit centralisé pour mettre à jour les prix si les tarifs Anthropic changent.

### API

- `GET /api/v1/projects/{project_id}/usage` — agrégat par projet (total tokens,
  coût total, coût par ticket)
- Inclure le coût de l'appel dans l'event WS existant du pipeline (ex.
  `agent_call_done`) pour un affichage en direct

### UI

Petit résumé de coût dans le panneau historique des pipelines (`ticket-018`) :
coût total du run, et éventuellement un total cumulé par projet dans la sidebar.

## Critères d'acceptation

- [ ] Chaque appel à un agent (`AgentRunnerService.run`) persiste ses tokens et
      son coût calculé en base
- [ ] `GET /api/v1/projects/{project_id}/usage` retourne un agrégat correct
      (somme tokens + somme coût) sur plusieurs runs
- [ ] Le panneau historique des pipelines affiche le coût du run
- [ ] Un changement de modèle (ex. `agent_config.model`) est bien reflété dans
      le calcul de coût (pas de prix hardcodé pour un seul modèle)

## Dépendances

Aucune — s'appuie sur la persistence SQLite existante (`ticket-015`) et le
logging déjà en place dans `agent_runner.py`.

## Estimation

**1.5j** — Migration SQLite + service de calcul de coût + endpoint + intégration
UI minimale.

## Risques

- **Faible** — Les prix par modèle doivent être maintenus à jour manuellement
  s'ils changent côté Anthropic ; pas de risque fonctionnel si oublié (juste un
  coût affiché obsolète).
