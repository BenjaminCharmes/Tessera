---
agent: codeur
created: 2026-10-29
depends_on: []
estimated_days: 2
id: ticket-669
plan: true
pr_number: null
priority: low
status: done
title: A provider for any OpenAI-compatible endpoint, declared by base URL
type: feat
---

# ticket-669 — Un fournisseur compatible OpenAI, déclaré par URL de base

## Objectif
Pouvoir confier un rôle sans outils à n'importe quel point d'accès compatible
OpenAI (OpenRouter, LM Studio, vLLM…), comme on le fait déjà avec Ollama.

## Contexte
Piste reçue le 29/10 d'une session tierce. Les fournisseurs vivent sous
`services/providers/` : `agent_sdk`, `anthropic_api`, `ollama`. Les services passent
toujours par `LLMProvider` (ADR-017), et `provider_pour_role` construit le
fournisseur de chaque rôle depuis `agents.json`, avec son repli (ADR-046). Les
jetons de services en ligne restent dans le `.env` (ADR-053).

## Solution proposée
- Un fournisseur `openai_compatible` qui appelle `POST {base_url}/chat/completions`,
  avec `complete` et `stream`, et la sortie structurée par `response_format`
  quand un schéma est donné (ADR-061).
- `agents.json` le déclare par rôle : `"provider": "openai_compatible"`,
  `"base_url"`, `"model"`. La clé, si besoin, se lit dans le `.env` par le nom
  d'une variable (`api_key_env`), jamais dans `agents.json`.
- Une indisponibilité déclenche le repli du rôle, comme pour Ollama.

## Critères d'acceptation
- [ ] Un test, avec un double HTTP, vérifie que `complete` envoie le modèle et les messages à `{base_url}/chat/completions` et rend le texte de la réponse
- [ ] Un test vérifie qu'un schéma part dans `response_format` et que la sortie structurée revient dans `ProviderResult.structured`
- [ ] Un test vérifie qu'une erreur de connexion déclenche le repli du rôle et l'événement `provider_fallback`
- [ ] Un test vérifie que la clé est lue dans l'environnement par `api_key_env`, et qu'un `agents.json` portant une clé en clair est refusé

## Ce que ça ne fait pas
- Ne donne d'outils à aucun rôle porté par ce fournisseur : comme Ollama, il sert les rôles sans outils.