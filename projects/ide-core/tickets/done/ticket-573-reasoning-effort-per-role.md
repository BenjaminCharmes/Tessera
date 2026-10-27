---
agent: codeur
created: 2026-10-24
depends_on: []
estimated_days: 0.5
id: ticket-573
pr_number: 698
priority: medium
status: done
title: Each role can declare its reasoning effort in agents.json
type: feat
---

# ticket-573 — Un effort de raisonnement par rôle

## Objectif
Pouvoir régler, rôle par rôle, l'effort de raisonnement du modèle : moins
pour la production et la documentation, plus pour la revue et la sécurité.

## Contexte
Veille du 24/10 : le SDK épinglé (0.2.159) accepte `ClaudeAgentOptions.effort`
(`low`, `medium`, `high`, `xhigh`, `max`). Tessera ne le fixe nulle part :
`_build_options` (`services/providers/agent_sdk.py`) n'en passe pas, et
`AgentConfig` (`models/agent.py`) n'a pas de champ pour le déclarer. Le gain
attendu est en jetons et en latence sur les rôles de production.

## Solution proposée
Un champ optionnel `effort` dans `AgentConfig`, limité aux cinq valeurs du
SDK. Absent : rien n'est passé au SDK, le comportement actuel ne change pas.
Présent : il atteint `_build_options` puis `ClaudeAgentOptions`. Les valeurs
des `agents.json` ne changent pas dans ce ticket (un agent ne les écrit pas) :
Benjamin les règle ensuite, après un essai sur des tickets déjà livrés.

## Critères d'acceptation
- [ ] `AgentConfig` de `backend/src/tessera/models/agent.py` a un champ `effort` optionnel limité à `low`, `medium`, `high`, `xhigh`, `max`, et un test montre qu'une autre valeur est refusée au chargement
- [ ] Un test montre que `_build_options` passe `effort` à `ClaudeAgentOptions` quand il est déclaré
- [ ] Un test montre que `_build_options` ne passe pas `effort` quand le rôle n'en déclare pas
- [ ] Le diff ne modifie aucun `agents.json`

## Ce que ça ne fait pas
- Ne choisit pas les valeurs par rôle.