---
agent: codeur
created: 2026-10-02
depends_on: []
estimated_days: 0.5
id: ticket-312
pr_number: 213
priority: high
status: done
title: The pricing grid and the default models move to the current Claude generation
type: fix
---

# ticket-312 — La grille de prix et les modèles par défaut passent à la génération actuelle

## Objectif

Pouvoir choisir les modèles Claude actuels dans l'écran Agents, et estimer
leur coût au bon tarif.

## Contexte

`services/cost_calculator.py` porte `_PRICING`, qui sert à deux choses :
estimer le coût d'un appel, qui alimente le plafond par run d'ADR-020, et
fournir la liste des modèles proposés à l'utilisateur (`modeles_connus`,
ticket-080). La grille date de la génération précédente :

- `claude-sonnet-5-5`, plus capable que `claude-sonnet-4-6` et moins cher
  (2 $ / 10 $ par million de tokens, contre 3 $ / 15 $), n'y figure pas. On ne
  peut donc pas le choisir à l'écran, et un appel à ce modèle serait estimé
  au tarif par défaut, soit 50 % trop haut.
- `claude-fable-5` y est tarifé 3 $ / 15 $, au lieu de 10 $ / 50 $.
- `claude-haiku-4-5` y est tarifé 0,80 $ / 4 $, au lieu de 1 $ / 5 $.
- `claude-opus-4-8` et `claude-opus-4-5` y sont tarifés 15 $ / 75 $, au lieu
  de 5 $ / 25 $.

Vérifié le 2026-10-02 : `claude-sonnet-5-5` répond par le SDK Agent sur
l'abonnement. Le CLI embarqué journalise `unrecognized_model`, mais c'est
bien ce modèle qui répond (`model_usage`).

Les modèles par défaut codés en dur sont restés sur `claude-sonnet-4-6` :
`agent_runner.py`, `agent_creator.py`, `planner.py`, `project_analyzer.py`
et `project_creator.py`. `chat_service.py` est sur `claude-sonnet-5`.

## Solution proposée

- `_PRICING`, aux tarifs publics du 2026-10-02 (entrée, sortie, lecture de
  cache, par million de tokens) :

  | Modèle | Entrée | Sortie | Cache |
  |---|---|---|---|
  | `claude-fable-5-1` | 10,00 | 50,00 | 0,25 |
  | `claude-opus-5-5` | 4,00 | 20,00 | 0,20 |
  | `claude-sonnet-5-5` | 2,00 | 10,00 | 0,20 |
  | `claude-haiku-4-5` | 1,00 | 5,00 | 0,10 |

  Les modèles déjà déclarés dans un `agents.json` (`claude-sonnet-4-6`,
  `claude-haiku-4-5-20251001`, `claude-fable-5`) restent dans la grille, aux
  bons tarifs, pour ne pas fausser l'historique.
- Les modèles par défaut codés en dur passent à `claude-sonnet-5-5`, dans une
  seule constante partagée au lieu de six.

## Critères d'acceptation

- [ ] Un test vérifie que `calculate_cost("claude-sonnet-5-5", 1_000_000,
      1_000_000, 0)` vaut 12,00
- [ ] Un test vérifie que `claude-fable-5-1`, `claude-opus-5-5`,
      `claude-sonnet-5-5` et `claude-haiku-4-5` figurent dans la liste des
      modèles disponibles
- [ ] Un test vérifie le tarif corrigé de `claude-fable-5` (10 $ / 50 $)
- [ ] Les six services cités importent une même constante de modèle par
      défaut, qui vaut `claude-sonnet-5-5`, et un test le vérifie
- [ ] Un test vérifie qu'un modèle inconnu est toujours estimé au tarif par
      défaut, sans lever d'exception

## Ce que ça ne fait pas

Les `agents.json` des projets ne sont pas modifiés : le choix du modèle par
rôle reste celui de l'utilisateur, à faire dans l'écran Agents une fois la
grille à jour.