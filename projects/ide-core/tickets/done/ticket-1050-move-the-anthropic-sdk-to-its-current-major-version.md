---
agent: codeur
created: 2026-11-24
depends_on: []
estimated_days: 1
id: ticket-1050
pr_number: 1272
priority: low
status: done
title: Move the anthropic SDK to its current major version
type: chore
---

# ticket-1050 — Passer le SDK `anthropic` à sa version majeure courante

## Objectif

Que le backend ne reste pas une version majeure en retard sur le SDK
`anthropic`, sans toucher à `httpx`.

## Contexte

Le radar de la semaine 47 relève que `backend/uv.lock` fige `anthropic` en
0.111.0 alors qu'une série 2.x existe. `backend/pyproject.toml` déclare
`anthropic>=0.28.0`. Le SDK n'est importé que par deux modules :
`backend/src/tessera/services/providers/anthropic_api.py` et
`backend/src/tessera/services/providers/__init__.py`. Les runs passent par
`claude-agent-sdk` et son CLI embarqué, que ce ticket ne touche pas.

Décision du 24/11 : faire cette montée ; garder `httpx` (22 modules l'importent,
aucune faille connue).

## Solution proposée

- Lire la section « Notes de migration » ci-dessous avant de changer le code.
- Relever la borne dans `backend/pyproject.toml` et régénérer `backend/uv.lock`
  pour le seul paquet `anthropic` (`uv lock --upgrade-package anthropic`).
- Adapter `anthropic_api.py` et les tests de ce provider à ce que la version
  change (noms d'exceptions, forme de `usage`, flux).
- Si la série 2.x n'existe pas sur l'index ou n'a pas de wheel Windows, ne rien
  changer et le dire dans le rapport.

## Notes de migration (vérifiées le 26/11 sur anthropic 2.14.0)

Le codeur n'a pas le web : ce qui suit a été relevé sur une installation réelle.

- **Dépendances** : `httpx2`, `httpcore2`, `opentelemetry-api`, `truststore`
  arrivent, toutes pure-Python. `httpx2` est un **module distinct**
  (`import httpx2`) : il cohabite avec `httpx`, rien n'est à renommer dans
  Tessera. `pydantic>=1.10` et `anyio>=4.1` : le lock actuel convient.
- **API** : le client envoie `anthropic-version: 2026-10-21` et la clé en
  `Authorization: Bearer` (plus `x-api-key`). `AsyncAnthropic(api_key=...)`
  ne change pas.
- **Paramètres** : `messages.create` et `messages.stream` n'acceptent plus
  `temperature`, `top_p` ni `top_k`. `anthropic_api.py` n'en passe aucun.
  `model`, `max_tokens`, `system`, `messages`, `tools`, `tool_choice` restent.
- **Inchangé, utilisé par `anthropic_api.py`** : `anthropic.types.TextBlockParam`
  (avec `cache_control`) ; `stream.text_stream` (async) et
  `await stream.get_final_message()` ; `usage.input_tokens`, `output_tokens`,
  `cache_read_input_tokens`, `cache_creation_input_tokens` ; les exceptions
  `APIError`, `APIStatusError`, `APIConnectionError`, `RateLimitError`,
  `AuthenticationError`, `InternalServerError`, `OverloadedError`.
- Le travail attendu est donc surtout le lock, la borne et des tests au
  client doublé ; ne pas réécrire le provider sans raison trouvée dans le code.

## Critères d'acceptation

- [ ] `backend/pyproject.toml` déclare `anthropic` avec une borne basse en 2.x.
- [ ] Le diff de `backend/uv.lock` porte `anthropic` en version 2.x.
- [ ] Le diff de `backend/pyproject.toml` ne modifie aucune ligne `httpx`.
- [ ] Un test de `anthropic_api.py` couvre `complete` et un test couvre
      `stream`, avec un client doublé à la forme de la nouvelle version.
- [ ] Le diff ne modifie pas la ligne `claude-agent-sdk` de
      `backend/pyproject.toml`.

## Ce que ça ne fait pas

- Ne remplace pas `httpx`.
- Ne monte ni `claude-agent-sdk` ni le CLI embarqué.

## Dépendances

Aucune.

## Estimation

Une journée.

## Risques

Smart App Control bloque certaines DLL selon leur réputation : une dépendance
transitive nouvelle peut casser l'import en local alors que la CI passe. À
vérifier sur le poste avant le merge.