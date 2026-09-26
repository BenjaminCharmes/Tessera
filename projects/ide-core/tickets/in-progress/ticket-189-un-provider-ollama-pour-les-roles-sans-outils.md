---
id: ticket-189
title: "Un provider Ollama sert les rôles sans outils sur un modèle local"
type: feat
status: in-progress
pr_number: null
priority: high
agent: codeur
depends_on: ["ticket-188"]
estimated_days: 2
created: 2026-09-26
---

# ticket-189 — Un provider Ollama sert les rôles sans outils sur un modèle local

## Objectif

Que les rôles qui ne font qu'un appel texte→JSON tournent sur un modèle
hébergé localement par Ollama, à coût nul, et retombent sur Claude quand
Ollama n'est pas là.

## Contexte

Le protocole `LLMProvider` (`services/providers/base.py`) est mono-tour et
texte→texte : `system`, `user`, un `ProviderResult`. Sept services l'utilisent
sans aucun outil : sécurité, validateur, doc-technique, doc-fonctionnelle,
planificateur, analyseur de projet, créateurs de projet et d'agent. Un
provider du niveau d'`AnthropicApiProvider` les sert tel quel.

Les rôles à outils — codeur, reviewer, architect, résolveur de conflit, chat
— dépendent du SDK Claude pour la boucle agentique, les hooks d'ADR-027 et
ADR-031, `max_turns`, le budget, `ask_user` et le quota. Ils restent hors
périmètre, exprès.

Les machines ne sont pas toutes équipées : 64 Go de RAM sur l'une, moins
ailleurs. Le repli du ticket-188 est ce qui rend le réglage portable d'une
machine à l'autre sans toucher au manifeste.

## Solution proposée

- `OllamaProvider` dans `services/providers/ollama.py`, en `httpx`, sur
  l'API native `POST /api/chat` : `stream: false` pour `complete`,
  `stream: true` pour `stream` avec `on_token` sur chaque fragment.
  `input_tokens` et `output_tokens` viennent de `prompt_eval_count` et
  `eval_count` ; `cost_usd = 0.0`, `provider_name = "ollama"`.
- `options.num_ctx` est **toujours** envoyé, depuis `max_tokens` du rôle
  plus la taille du prompt, avec un plancher de 16 384 : le défaut d'Ollama
  est 4 096, ce qui tronquerait silencieusement le diff de 16 000 caractères
  que reçoit l'audit sécurité.
- Délai de lecture `httpx` à 300 s : un modèle qui se charge en mémoire
  prend plus que les 5 s par défaut.
- `ProviderIndisponible` (ticket-188) est levée sur connexion refusée, délai
  dépassé, ou modèle absent de `GET /api/tags`. Le modèle n'est **jamais**
  tiré automatiquement : 19 Go ne se téléchargent pas en silence au milieu
  d'un run.
- Réglages : `ollama_base_url` dans `config.py`, défaut
  `http://127.0.0.1:11434`.
- `get_provider` accepte `"ollama"`.
- Rôles et modèles à déclarer dans `agents.json` de `ide-core` et de
  `demineur`, au titre de ce ticket :

  | Rôle | provider | model | repli |
  |---|---|---|---|
  | securite | ollama | `qwen3-coder:30b` | agent_sdk, `claude-haiku-4-5` |
  | validateur | ollama | `qwen3-coder:30b` | agent_sdk, `claude-haiku-4-5` |
  | doc-technique | ollama | `qwen3-coder:30b` | agent_sdk, `claude-haiku-4-5` |
  | doc-fonctionnelle | ollama | `qwen3-coder:30b` | agent_sdk, `claude-haiku-4-5` |
  | project-analyzer | ollama | `qwen3-coder:30b` | agent_sdk, `claude-sonnet-4-6` |

  Un seul modèle pour tous : `qwen3-coder:30b` est un MoE à 3 milliards de
  paramètres actifs, environ 19 Go en quantification 4 bits, avec une
  fenêtre longue — rapide sur CPU avec 64 Go, et un seul chargement en
  mémoire pour les cinq rôles. Le nom exact est un réglage, pas une
  décision : si un modèle plus récent le remplace, seul le manifeste change.
  Planificateur, créateurs de projet et d'agent restent sur Claude : rares,
  et leur sortie structure tout ce qui suit.
- Le repli sur Haiku plutôt que Sonnet pour les rôles de jugement : ce sont
  des appels uniques sur un diff borné, et la ventilation des coûts montre
  que Sonnet y était surdimensionné.

## Critères d'acceptation

- [ ] `OllamaProvider` satisfait `LLMProvider` (`isinstance` sur le protocole
      `runtime_checkable`)
- [ ] Un test `respx` vérifie `complete` : requête `/api/chat` avec `num_ctx`
      ≥ 16 384, réponse parsée, tokens lus, `cost_usd == 0.0`
- [ ] Un test vérifie `stream` : `on_token` reçoit chaque fragment, et le
      contenu final est identique à la concaténation
- [ ] Un test vérifie `ProviderIndisponible` sur connexion refusée, sur délai
      dépassé, et sur modèle absent de `/api/tags`
- [ ] Un test vérifie qu'aucune requête `POST /api/pull` n'est jamais émise
- [ ] Un test de bout en bout : projet dont `securite` est sur `ollama` avec
      repli `agent_sdk`, Ollama injoignable, l'audit rend son verdict via le
      repli et l'événement `provider_fallback` est émis
- [ ] `agents.json` de `ide-core` et `demineur` déclarent les cinq rôles du
      tableau, et chargent
- [ ] `README.md` décrit `OLLAMA_BASE_URL` et le modèle à installer
      (`ollama pull qwen3-coder:30b`)
- [ ] `uv run mypy src/` passe

## Ce que ça ne fait pas

Pas de codeur, reviewer, architect, résolveur ni chat sur Ollama : il
faudrait réécrire la boucle agentique et rebrancher les gardes d'ADR-027 et
ADR-031. Un ticket `design` sera ouvert si ce ticket montre qu'un modèle
local tient sur les rôles de jugement. Pas d'API OpenAI-compatible : l'API
native suffit et rend les compteurs de tokens. Pas de choix automatique du
modèle selon la RAM disponible.

## Dépendances

ticket-188.

## Estimation

2 jours.

## Risques

ADR-039 fait échouer fermé sécurité et validateur : un modèle local qui rend
un JSON illisible **bloque** des runs. Le repli ne couvre pas ce cas, exprès.
La ventilation des coûts par modèle et le taux de `reason` non vide sur ces
deux étapes sont ce qui dira, après une semaine, si le modèle choisi tient.
Prévoir de comparer sur les mêmes diffs le verdict Ollama et le verdict
Claude avant de généraliser.
