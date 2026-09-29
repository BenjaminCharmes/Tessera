---
id: ticket-243
title: "Un ticket peut demander un plan avant le code"
type: feat
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-29
---

# ticket-243 — Un ticket peut demander un plan avant le code

## Objectif

Un ticket qui déclare `plan: true` dans son frontmatter passe, avant le premier
tour du codeur, par un agent en lecture seule qui rend un plan : les étapes, et
pour chaque critère d'acceptation, l'étape qui le couvre.

## Contexte

Le pipeline enchaîne codeur → tests → sécurité → reviewer → validateur. Il n'y
a pas de phase de plan : une erreur d'approche sur un gros ticket ne se voit
qu'au reviewer, après un tour de code complet, et le ticket-213 a épuisé ses
trente actions sans finir. Le planificateur existant découpe une feature en
tickets, il ne prépare pas un ticket.

## Solution proposée

- `Ticket.plan: bool`, lu du frontmatter ; seul un vrai booléen YAML l'active.
- `pipeline_plan.run_plan` : rôle `plan`, prompt `agents/prompts/plan.md`, modèle
  du codeur, outils de relecture (`Read`, `Glob`, `Grep`) et plafond de tours du
  reviewer.
- Le plan entre dans `build_context` sous « Plan retenu avant le code » : le
  codeur le suit, le reviewer juge l'écart.
- Les événements partent sous le rôle `codeur`, avec `phase: "plan"` et
  `round: 0` : le fil du ticket l'affiche sans changement côté UI.
- Un plan qui échoue est journalisé, et le run continue sans lui.

## Critères d'acceptation

- [ ] `test_plan_avant_le_code.py` vérifie qu'un ticket à `plan: true` appelle `plan`, puis le codeur, puis le reviewer, et que le plan est dans le contexte des deux derniers
- [ ] `test_plan_avant_le_code.py` vérifie qu'un ticket sans `plan` n'appelle pas le rôle `plan`
- [ ] `test_plan_avant_le_code.py` vérifie qu'un plan qui lève laisse le run aller jusqu'à l'approbation
- [ ] `test_plan_avant_le_code.py` vérifie qu'un `AGENT_DONE` à `phase: "plan"` porte le plan, sous le rôle `codeur`
- [ ] `test_plan_avant_le_code.py` vérifie que le provider du rôle `plan` n'a que `OUTILS_DE_RELECTURE`
- [ ] `test_plan_avant_le_code.py` vérifie que `plan: "oui"` n'active pas le plan

## Ce que ça ne fait pas

- Pas de porte : un plan n'est pas approuvé ou refusé avant le code. Le
  reviewer juge l'écart au diff.
- Pas de case à cocher dans l'UI de création de ticket : le champ s'écrit dans
  le frontmatter.
- Le codeur ne reprend pas la session du plan : les deux n'ont ni le même
  prompt ni les mêmes outils, et une reprise ratée rejouerait un prompt de
  reprise sans le ticket.
