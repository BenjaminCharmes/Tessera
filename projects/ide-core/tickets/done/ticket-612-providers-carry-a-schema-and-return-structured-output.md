---
agent: codeur
created: 2026-10-27
depends_on:
- ticket-611
estimated_days: 1
id: ticket-612
priority: medium
status: done
title: Providers accept a JSON schema and return the validated structured output
type: feat
---

# ticket-612 — La plomberie du schéma dans `LLMProvider`

## Objectif
Qu'un appelant passe un schéma JSON à un provider et reçoive la sortie
validée, sans que `services/` touche au SDK (ADR-017, ADR-061).

## Interface (fixée par ADR-061)
- `ProviderResult.structured: dict[str, Any] | None = None` — la sortie validée ;
  `None` quand le provider n'en a pas rendu. `content` garde le texte.
- `complete(..., schema: dict[str, Any] | None = None)` et `stream(...)` de même.
  Comme `session` et `ask_user`, le paramètre n'est transmis que s'il est posé :
  un provider ou un double de test qui l'ignore ne le voit jamais.
- Schéma en JSON Schema draft-07, sans mot-clé numérique (`minimum`, `maximum`) :
  les bornes se vérifient dans le code appelant.
- SDK : `ClaudeAgentOptions.output_format = {"type": "json_schema", "schema": …}` ;
  lire `ResultMessage.structured_output`. Un `success` sans sortie, ou le sous-type
  `error_max_structured_output_retries`, rend `structured=None`. Les appels
  `StructuredOutput` ne partent pas dans `on_tool_use`.
- Ollama : champ `format` du corps de `/api/chat` (`_corps`, `providers/ollama.py`) ;
  parser `message.content` en JSON, `None` si invalide ou coupé par `num_predict`.
- API Anthropic : un outil unique dont `input_schema` est le schéma, avec
  `tool_choice` forcé ; la sortie est l'`input` du `tool_use`.
- `ProviderAvecRepli` : le même schéma passe au repli (ADR-046) ; une sortie
  invalide du principal ne déclenche pas le repli, seule l'indisponibilité le fait.
- `AgentRunner.run(..., schema=None)` (`services/agent_runner.py`) le transmet au
  provider, et `AgentResult.structured` reprend `ProviderResult.structured`. Le
  reviewer passe par ce chemin, pas par `provider.complete` directement.
- Si le ticket-611 a nommé un réglage de `_build_options`, il s'applique ici.

## Critères d'acceptation
- [ ] `ProviderResult.structured` existe, vaut `None` par défaut, et les trois providers le renseignent quand un schéma est posé (un test par provider, avec un double du transport)
- [ ] Sans `schema`, aucun provider ne change de comportement : le test existant du protocole passe sans modification et un test vérifie que `schema` n'est pas transmis à un double qui ne l'accepte pas
- [ ] Un `success` sans `structured_output`, `error_max_structured_output_retries` et un JSON Ollama tronqué rendent chacun `structured=None`, testés
- [ ] Un bloc `StructuredOutput` n'arrive pas à `on_tool_use`, testé
- [ ] `ProviderAvecRepli` transmet le schéma au repli, et une sortie invalide ne déclenche aucun repli, testés
- [ ] `AgentRunner.run` transmet `schema` et `AgentResult.structured` reprend la sortie du provider, testés ; sans `schema`, rien ne change
- [ ] `LLMProvider` documente `schema` dans sa docstring, avec la limite des bornes numériques

## Ce que ça ne fait pas
- Aucun service ne passe encore de schéma : tickets 613 et 614.
- Ne relance pas un appel sur sortie invalide : le SDK relance déjà de lui-même, et le refus est l'affaire du service.