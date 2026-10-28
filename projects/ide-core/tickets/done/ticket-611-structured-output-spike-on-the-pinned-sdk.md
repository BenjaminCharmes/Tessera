---
agent: codeur
created: 2026-10-27
depends_on: []
estimated_days: 0.5
id: ticket-611
priority: medium
status: done
title: 'Spike: structured output on the pinned SDK keeps the reviewer''s tool turns'
type: chore
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
## Résultat

Mesuré le 2026-10-28 sur le SDK épinglé `claude-agent-sdk 0.2.159` (CLI embarqué
2.1.281), avec les options exactes de `_build_options` (`tools` et `allowed_tools`
= `Read`, `Glob`, `Grep`, comme `OUTILS_DE_RELECTURE`) auxquelles on ajoute
`output_format = {"type": "json_schema", "schema": …}` après coup. Le schéma est
celui du ticket-614. Script : `scripts/mesurer_structured_output.py`
(`python ../scripts/mesurer_structured_output.py <outils|tours|relances|schema|sequentiel|on_tool_use|ligne>`,
depuis `backend/`). Appels réels sur haiku 4.5, sauf une confirmation sur
`claude-opus-5-5` (le modèle du reviewer d'ide-core). Aucun fichier de
`backend/src/` modifié. ADR-061 n'est contredite par aucune mesure.

1. **`StructuredOutput` disponible : oui, sans réglage.** Le message `init` liste
   `['Glob', 'Grep', 'Read', 'StructuredOutput']` avec `tools` et `allowed_tools`
   explicites ; le SDK l'ajoute seul (haiku et opus, même liste).
2. **Tours de lecture gardés : oui, mais `StructuredOutput` consomme un tour, et
   chaque relance de validation aussi.**
   - `llm_max_turns_reviewer` vaut **10** (`config.py:91`) ; `agents.json` ne le
     surcharge pas.
   - Lectures successives `Read`, `Read` puis `StructuredOutput` : succès à
     `max_turns=3` (2 essais sur 2), `error_max_turns` à `max_turns=2` (2 sur 2).
     Trois lectures successives : succès à 10, `error_max_turns` à 2.
   - Première tentative rejetée par la validation puis corrigée (deux appels
     `StructuredOutput`) : succès à `max_turns=10` (`num_turns=3`),
     `error_max_turns` à 2 et à 1. Une relance consomme donc du `max_turns`.
   - L'échec de plafond sort **en exception** : le SDK lève
     `ResultError: Reached maximum number of turns (N)` au lieu de rendre le
     `ResultMessage` (`subtype='error_max_turns'`, `structured_output=None`).
   - **Contournement : relever `llm_max_turns_reviewer` de 1 (11).** Coût : un
     tour de plus au plus par revue, dépensé seulement quand le reviewer lit
     jusqu'au plafond. Sans cela, 9 tours restent aux lectures, moins un par
     relance. Même décalage pour la sécurité : `_budget_note` annonce « au plus N
     lectures », il en reste N − 1. Au ticket-612/614 de trancher.
3. **`structured_output` après des tours d'outils : présent et conforme.** 5 appels
   haiku avec lectures validés avec `jsonschema` (`Draft7Validator`) contre le schéma
   du reviewer : 0 erreur. Opus : un objet avec `verdict`, `summary`, `blocking`,
   `suggestions`. **Piège mesuré :** `subtype='success'` avec
   `structured_output=None` existe. (a) Consigne qui contredit le schéma : le
   modèle répond en texte, aucun appel `StructuredOutput`. (b) Schéma
   insatisfiable : deux appels rejetés, puis `success` et `None` ; le sous-type
   `error_max_structured_output_retries` n'est pas apparu. Le ticket-612 doit
   traiter `success` sans sortie comme un échec, ce qu'il prévoit déjà.
4. **CLI embarqué : 2.1.281, donc ≥ 2.1.205.** `claude.exe --version` rend
   `2.1.281 (Claude Code)`, comme `_cli_version.py`. Schéma invalide
   (`"type": "pas-un-type"`) : erreur, pas silence — le processus sort en code 1
   avant le message `init`, et le SDK lève `ProcessError: Command failed with
   exit code 1`. Le message ne dit pas la cause (stderr n'est pas relayé).
5. **Ligne de commande Windows** (`list2cmdline` sur `_build_command()`, limite
   32 767) : le schéma du reviewer fait 439 caractères, +534 sur la ligne
   quotée. Avec `reviewer.md` (4 225 octets) : **5 092** avec schéma (4 558
   sans), marge **6,4×**. Pire cas, prompt système juste sous le seuil de
   `SYSTEM_PROMPT_FILE_THRESHOLD_BYTES` (24 000) : **25 081**, marge 1,3×, sous
   les 2× visés. La marge de 2× tient jusqu'à ~15 300 caractères de prompt
   système. Le prompt utilisateur (diff, ticket) passe par stdin
   (`--input-format stream-json`), pas par la ligne. Écrire le schéma en anglais :
   `json.dumps` échappe les accents (`\u00e9`) et gonfle la ligne.
6. **`StructuredOutput` dans `on_tool_use` : oui.** Via
   `ClaudeAgentSDKProvider.stream` avec `output_format` posé, le callback reçoit
   `['Read', 'Read', 'Grep', 'StructuredOutput']`. Le filtre du ticket-612 est
   nécessaire.

**Limites de la mesure.** Une seule lecture de pire cas par modèle ; le nombre de
tours dépend du modèle (lectures parallèles ou successives), d'où les deux essais
par plafond. Les plafonds ont été mesurés sur haiku ; opus n'a été rejoué qu'une
fois, au plafond 10.