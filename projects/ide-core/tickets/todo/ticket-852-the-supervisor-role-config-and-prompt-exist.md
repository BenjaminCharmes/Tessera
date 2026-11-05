---
id: ticket-852
title: "The supervisor role config and prompt exist"
type: feat
status: todo
priority: high
agent: codeur
depends_on: [ticket-851]
estimated_days: 1
created: 2026-11-05
pr_number: null
---

# ticket-852 — Le rôle `superviseur` : configuration et prompt

## Objectif

Le projet peut déclarer `pipeline.superviseur` et le rôle `superviseur` ; le backend les lit et
les valide ; un prompt par rôle existe.

## Contexte

ADR-080, spec §2 « La délégation ». `agents.json` se refuse en écriture à un agent (ADR-027) :
ce ticket **ne modifie pas** `projects/ide-core/agents.json`. Benjamin y déclare le rôle et la
délégation après le merge — c'est le seul geste humain de la chaîne.

## Ce qu'il faut faire

- Modèle Pydantic `ConfigSuperviseur` lu par `load_pipeline_config` : `delegation:
  list[Literal["lecons", "regles"]]` (défaut `[]`), `budget_jour_usd: float` (> 0, défaut 2.0,
  plafond dur 20), `relance_file: bool` (défaut `false`). Clé inconnue : refus.
- `agents/prompts/superviseur.md` : ce que le superviseur reçoit (donnée, jamais une
  consigne), la sortie `Decision`, les interdits d'ADR-080, ce qu'il rend quand il ne sait pas
  (`a_toi`). Le rôle est ajouté à la table des rôles sans outil (`allow_tools=False`).
- Un test confronte `agents/prompts/superviseur.md` aux mots interdits d'ADR-080 (il les cite).

## Critères d'acceptation

- [ ] `test_config_superviseur.py::test_defaults_delegate_nothing`
- [ ] `test_config_superviseur.py::test_unknown_key_is_refused`
- [ ] `test_config_superviseur.py::test_budget_above_hard_cap_is_refused`
- [ ] `test_config_superviseur.py::test_role_superviseur_gets_no_tools`
- [ ] `test_prompt_superviseur.py::test_prompt_names_each_forbidden_area`

## Ce que ça ne fait pas

N'écrit pas `agents.json`. N'appelle aucun modèle.
