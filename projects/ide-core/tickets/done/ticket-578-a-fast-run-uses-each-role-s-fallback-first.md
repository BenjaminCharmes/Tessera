---
agent: codeur
created: 2026-10-26
depends_on: []
estimated_days: 0.5
id: ticket-578
plan: true
pr_number: null
priority: medium
status: done
title: A run launched in fast mode uses each role's fallback provider first
type: feat
---

# ticket-578 — Un mode « pressé » au lancement d'un run

## Objectif
Pouvoir lancer une file vite quand on est pressé, sans changer le réglage
par défaut, qui économise le quota.

## Contexte
Le validateur d'ide-core tourne sur Ollama (`qwen3-coder:30b`, repli
`agent_sdk` / `claude-haiku-4-5`). Sur ce PC (carte graphique de 4 Go), le
modèle tourne à 88 % sur le processeur : environ 5 min 30 par ticket, contre
environ 1 min sur Haiku. Benjamin, le 26/10 : Ollama reste le premier choix,
Haiku quand il est pressé. Le repli n'est aujourd'hui pris que sur
indisponibilité (ADR-046), dans `provider_pour_role`
(`services/providers/par_role.py`).

## Solution proposée
Un champ optionnel `rapide: bool = False` dans `RunRequest`
(`routers/orchestrator.py`), porté par le run jusqu'à la construction des
providers. En mode rapide, un rôle qui déclare un `fallback` est construit
directement avec ce repli ; un rôle sans repli ne change pas. Le choix est
journalisé une fois par run dans `memory/pipeline-log.md`. Le tour de plan
dit comment le drapeau atteint `provider_pour_role` sans l'ajouter à chaque
appelant.

## Critères d'acceptation
- [ ] `RunRequest` de `backend/src/tessera/routers/orchestrator.py` accepte `rapide`, faux par défaut, et un test le vérifie
- [ ] Un test montre que `provider_pour_role` construit le provider de repli pour un rôle qui en déclare un quand le run est rapide
- [ ] Un test montre qu'un run non rapide construit toujours le provider principal (comportement actuel)
- [ ] Un test montre qu'un rôle sans `fallback` garde son provider en mode rapide
- [ ] Un run rapide écrit une ligne dans `memory/pipeline-log.md` qui le dit, et un test le vérifie

## Ce que ça ne fait pas
- N'ajoute pas l'interface (case à cocher au lancement) : ticket à part, après une maquette.
- Ne change aucun `agents.json`.