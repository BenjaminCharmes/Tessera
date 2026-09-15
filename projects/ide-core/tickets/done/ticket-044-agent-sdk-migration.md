---
id: ticket-044
title: "Migration vers le Claude Agent SDK (abonnement + outils fichier)"
type: feat
status: done
pr_number: 60
priority: high
agent: codeur
depends_on: []
estimated_days: 3
created: 2026-09-14
---

# ticket-044 — Migration vers le Claude Agent SDK

> **Note** : ticket rédigé rétrospectivement (2026-09-15). L'implémentation a été
> livrée par la PR #60 avant que le ticket n'existe — c'est précisément l'écart de
> process que ce fichier corrige. Voir [ticket-046](../todo/ticket-046-decomposer-orchestrator.md)
> pour le suivi.

## Objectif

Permettre à vibe-ide de fonctionner sur l'**abonnement Claude** plutôt que sur des
crédits API prépayés, et donner aux agents la capacité d'**écrire réellement des
fichiers** au lieu de produire de la prose que personne n'applique.

## Contexte

Deux blocages empêchaient l'usage quotidien de l'IDE :

1. **Coût** — chaque appel passait par la Messages API, facturée au token. Sans
   crédits prépayés, l'IDE ne démarre pas.
2. **Les agents n'écrivaient rien** — le codeur retournait du texte décrivant le
   code, jamais appliqué au dépôt. Le reviewer relisait donc de la prose.

## Solution livrée

### Abstraction `LLMProvider`

Un protocole `complete` / `stream` avec deux implémentations :

- **`ClaudeAgentSDKProvider`** (défaut, `llm_provider="agent_sdk"`) — backé par le
  Claude Agent SDK, facturé sur l'abonnement, dispose des outils fichier.
- **`AnthropicApiProvider`** (fallback, `llm_provider="anthropic_api"`) — Messages
  API directe, pour les environnements sans session interactive (Docker, CI).

`get_provider()` construit l'un ou l'autre selon `settings.llm_provider`.

### Garde-fous

Voir **ADR-017** dans `memory/decisions.md` pour le détail des invariants :
`cwd` toujours résolu, configuration des outils toujours explicite (`tools` **et**
`allowed_tools`), et variante `allow_tools=False` pour les services non-agentiques.

### Quotas

- `llm_max_turns=30` — borne les allers-retours outil d'un agent qui dérape
- `llm_max_budget_usd=1.0` — borne la dépense d'un seul appel agent

## Critères d'acceptation

- [x] `get_provider()` retourne le provider Agent SDK par défaut
- [x] Le provider API reste utilisable via `llm_provider="anthropic_api"`
- [x] Les agents écrivent réellement sur le disque via les outils fichier
- [x] Les services non-agentiques reçoivent un provider sans outils
- [x] ADR-017 documente la décision et ses invariants

## Dépendances

Aucune.

## Estimation

**3j** — spike + abstraction provider + migration des services + tests.
