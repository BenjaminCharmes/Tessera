---
id: ticket-702
title: "The codeur's exhausted turns are recorded and journalised"
type: feat
status: todo
priority: low
agent: codeur
created: 2026-10-30
---

# ticket-702 — L'épuisement des actions du codeur se journalise

## Objectif
Savoir combien d'appels de codeur finissent sur la limite d'actions
(`llm_max_turns`), aujourd'hui invisible, pour décider avec un nombre si les
sous-tâches dans un run doivent rouvrir (ADR-066).

## Contexte
`providers/agent_sdk.py` (fin de `complete`, ≈ lignes 449-464) lit du
`ResultMessage` le coût, les tokens et `session_id`, jamais `num_turns` ni
`subtype`. La documentation du SDK
(https://code.claude.com/docs/en/agent-sdk/python) dit qu'à l'épuisement
`subtype == "error_max_turns"` et `is_error == True`. Le travail partiel part
aux tests comme un travail fini, sans trace. Spec :
`docs/superpowers/specs/2026-10-30-sous-taches-dans-un-run-design.md`, §1 et §4.

## Critères d'acceptation
- [ ] `ProviderResult` porte `num_turns: int | None = None` et `max_turns_reached: bool = False` ; le provider Agent SDK les remplit depuis `ResultMessage.num_turns` et `subtype == "error_max_turns"`, et les autres providers gardent les défauts
- [ ] Un test de `test_provider_agent_sdk.py` construit un `ResultMessage` de `subtype="error_max_turns"` et vérifie les deux champs ; un second, de `subtype="success"`, vérifie `max_turns_reached is False`
- [ ] Après un tour de codeur, le pipeline écrit au journal `[ticket-NNN] tour N — codeur : actions épuisées (<num_turns>/<limite>)` quand `max_turns_reached` est vrai, et rien sinon ; un test avec un runner factice couvre les deux cas
- [ ] L'événement `AGENT_DONE` du codeur porte `turns` et `turns_exhausted` ; la PR nomme le chemin que la valeur suit du provider à l'étape du codeur
- [ ] Le déroulé du run est inchangé : un travail partiel part aux tests comme avant, aucun refus nouveau, aucun repli déclenché
- [ ] `uv run pytest` et `uv run mypy` passent

## Ce que ça ne fait pas
- N'implémente aucune sous-tâche (ADR-066 les écarte)
- Ne change ni `llm_max_turns` ni aucun autre plafond
- Ne touche ni à la base de données (pas de migration) ni à l'interface
- Ne déclenche aucune alerte : le seuil de réouverture se relève à la main, par `Grep` sur le journal
