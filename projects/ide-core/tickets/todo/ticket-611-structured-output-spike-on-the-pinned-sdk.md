---
id: ticket-611
title: "Spike: structured output on the pinned SDK keeps the reviewer's tool turns"
type: chore
status: todo
priority: medium
agent: codeur
created: 2026-10-27
depends_on: []
estimated_days: 0.5
---

# ticket-611 — Vérifier `output_format` avec les outils du reviewer

## Objectif
Établir, par des appels réels sur le SDK épinglé, ce que la doc ne dit pas :
l'effet de `output_format` sur un agent qui lit du code avant de conclure. Les
tickets 612 à 615 (ADR-061) reposent sur ces réponses.

## Contexte
Doc : https://code.claude.com/docs/en/agent-sdk/structured-outputs. Le SDK
ajoute un outil `StructuredOutput`, valide la sortie, relance l'agent sur un
écart, et termine en `error_max_structured_output_retries` si aucune tentative
ne passe. Un résultat `success` sans `structured_output` est un échec. Le
schéma part au CLI par `--json-schema`, sur la ligne de commande. Avant le CLI
2.1.205, un schéma invalide était ignoré en silence.
`_build_options` (`providers/agent_sdk.py`) donne `tools=` explicite : rien ne
dit que `StructuredOutput` y survit.

## À mesurer
1. Avec `tools` et `allowed_tools` explicites comme dans `_build_options`,
   `StructuredOutput` est-il disponible ? Sinon, quel réglage le rend-il ?
2. Le reviewer garde-t-il ses tours de lecture (relever son `max_turns`
   réel) ? Les relances de validation consomment-elles `max_turns` ?
3. `ResultMessage.structured_output` après des tours d'outils : présent, et
   conforme au schéma ?
4. Le CLI embarqué est-il ≥ 2.1.205 (schéma invalide → erreur, pas silence) ?
5. Longueur de la ligne de commande Windows avec le schéma du reviewer
   (ticket-614) ; limite visée : 32 767 caractères, marge d'au moins 2×.
6. Le bloc `StructuredOutput` apparaît-il dans `on_tool_use` ? (À filtrer.)

## Critères d'acceptation
- [ ] Le ticket, dans une section « Résultat », répond aux six questions avec la mesure faite et sa valeur
- [ ] Si la réponse à la question 1 ou 2 est négative, le ticket nomme le réglage ou le contournement, et ce qu'il coûte
- [ ] Aucun fichier de `backend/src/` n'est modifié ; le script de mesure, s'il y en a un, reste hors du dépôt ou sous `scripts/` et est cité dans la section « Résultat »

## Ce que ça ne fait pas
- Ne branche aucun schéma dans le pipeline : c'est le ticket-612.
- Ne tranche pas le format : ADR-061 est prise. Si une mesure la contredit, le ticket le dit et passe en `blocked` plutôt que de la contourner.
