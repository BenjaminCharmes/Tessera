---
id: ticket-054
title: "Suivre le quota réel de l'abonnement, pas seulement la dépense estimée"
type: feat
status: done
pr_number: null
priority: high
agent: codeur
depends_on: [ticket-052]
estimated_days: 2
created: 2026-09-15
---

# ticket-054 — Suivi du quota d'abonnement

## Objectif

Savoir **combien il reste** avant d'être bloqué, au lieu de l'estimer.

## Contexte

[ticket-052](../done/ticket-052-budget-cumulatif-run.md) borne la dépense
**estimée** d'un run, calculée à partir des tokens et d'une grille tarifaire.
C'est un garde-fou utile, mais il ne mesure pas la bonne chose : en mode
abonnement — le mode par défaut — la ressource finie n'est pas un montant en
dollars, c'est un **quota de fenêtre glissante** imposé par le fournisseur.

Conséquences aujourd'hui :

- Un run peut être coupé en plein vol par une limite de débit sans qu'aucun
  plafond local n'ait été atteint, avec un message brut
- L'utilisateur ne sait jamais où il en est avant d'être bloqué
- `RUN_MAX_BUDGET_USD` et `CHAT_MAX_CONVERSATION_USD` se règlent à l'aveugle

Ce manque est explicitement noté en fin de ticket-052 et dans l'issue #61.

## Solution proposée

1. **Capter les événements de limite** que le SDK remonte, dans
   `ClaudeAgentSDKProvider`, et les normaliser en un modèle interne — ne pas
   laisser fuiter la forme du SDK dans le reste du code.
2. **`QuotaTracker`** — conserve le dernier état connu : proportion consommée,
   horodatage de réinitialisation, source (abonnement ou crédits API).
3. **Événement WebSocket** pour que l'UI l'affiche sans interroger en boucle.
4. **Arrêt anticipé** du mode autonome quand le quota restant ne suffit
   manifestement plus à un ticket complet — mieux vaut s'arrêter entre deux
   tickets que se faire couper au milieu d'un (même raison qu'en ticket-052).
5. **Dégradation propre** : si le provider ne remonte rien, le tracker reste
   vide et rien ne casse. Le mode `anthropic_api` n'a pas de quota
   d'abonnement.

## Critères d'acceptation

- [x] Les événements de limite du SDK sont captés et normalisés
- [x] `QuotaTracker` expose la proportion consommée et l'heure de réinit
- [x] L'état du quota est diffusé via WebSocket et visible dans l'UI
- [x] Le mode autonome s'arrête **entre deux tickets** quand le quota est bas
- [x] Un provider muet laisse le tracker vide, sans rien casser
- [x] Le mode `anthropic_api` n'affiche pas de quota d'abonnement
- [x] `uv run pytest -q` et `uv run mypy src/` verts

## Dépendances

`ticket-052` — le point d'arrêt entre tickets existe déjà, ce ticket lui
ajoute une seconde condition.

## Estimation

**2j**.

## Risques

- **Moyen** — la forme des événements dépend de la version du SDK. Mitigation :
  la normaliser derrière un modèle interne dès la capture, et traiter l'absence
  d'événement comme le cas nominal plutôt que comme une erreur.

## Livré

| Couche | Contenu |
|---|---|
| `quota_tracker.py` | `QuotaSnapshot`, `QuotaTracker`, normalisation depuis le SDK |
| `providers/agent_sdk.py` | Capture des `RateLimitEvent` dans la boucle de messages |
| `orchestrator.py` | Seconde condition d'arrêt, entre deux tickets (ADR-020) |
| `pipeline_events.py` | Événement `quota_updated` |
| Frontend | `QuotaBadge`, quota suivi dans `useOrchestratorStream` |

Le SDK expose `RateLimitInfo` avec `status`, `utilization`, `resets_at` et
`rate_limit_type` — exactement ce qu'il fallait. La forme du SDK est normalisée
dès la capture et ne va pas plus loin.

## Effet de bord corrigé

L'union `EventType` du frontend était restée à **six** valeurs alors que le
pipeline en émet **quinze** : les neuf manquantes traversaient l'UI sans type,
donc sans traitement possible, et rien ne le signalait.
`test_event_types_alignment.py` garde désormais les deux côtés alignés, dans
les deux sens.
