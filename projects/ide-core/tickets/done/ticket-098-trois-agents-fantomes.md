---
id: ticket-098
title: "L'architecte travaille, une suite rouge renvoie au codeur"
type: feat
status: done
pr_number: null
priority: high
agent: codeur
depends_on: [ticket-097]
estimated_days: 1
created: 2026-09-18
---

# ticket-098 — Les trois agents qui ne parlaient jamais

## Pourquoi

Question posée après que le badge les a révélés : « ce sont des agents utiles
dans la plupart des cas, non ? ». Oui pour deux d'entre eux. Trois histoires
différentes.

### `testeur` — le travail est fait, mais pas par un agent

Le prompt (ticket-035) demandait à un modèle de transformer la sortie brute des
tests en JSON. L'implémentation a pris une autre route : `TestRunnerService` la
parse par expression régulière. C'est le bon choix — lire « 42 passed in 3.2s »
avec une regex est gratuit, instantané et déterministe, là où un modèle coûte
un appel et peut inventer un chiffre.

**Mais le vrai trou était ailleurs** : une suite rouge n'était qu'ajoutée au
contexte du reviewer. Un ticket dont les tests cassent pouvait être approuvé
par un reviewer qui n'avait pas regardé la ligne rouge.

### `architect` — une promesse jamais tenue

Déclaré depuis le premier commit, annoncé par `ide-core/CLAUDE.md` comme
intervenant sur les tickets `design`. **Rien ne routait par type.**
`TicketType.design` existait sans qu'aucune décision ne le lise.

### `orchestrateur` — remplacé par mieux

L'orchestration est le cœur de l'IDE, mais elle est faite par du **code** :
séquence, tours de revue, plafonds, conditions d'arrêt. `pick_next_ticket()`
choisit le prochain ticket en huit lignes. Confier ça à un modèle coûterait un
appel par décision et rendrait un run impossible à rejouer. ADR-002 dit qu'on
écrit notre propre boucle : la boucle, c'est du code.

## Critères d'acceptation

- [x] Une suite rouge renvoie au codeur **sans appeler le reviewer** — un
      appel économisé, et un fait déjà établi qu'on ne fait pas arbitrer
- [x] Le codeur reçoit le résumé **et les erreurs** : sans elles, le second
      tour recommence à l'aveugle
- [x] L'absence de testeur ou de commande détectée n'est pas un échec
- [x] Une panne du lanceur lui-même ne devient pas un échec du ticket
- [x] Un ticket `design` va à l'architecte ; `feat`, `fix`, `chore` au codeur
- [x] `testeur.md` et `orchestrateur.md` supprimés, avec leurs déclarations
- [x] Plus aucun agent « jamais appelé »

## Ce que ça a révélé au passage

**La suite de tests écrivait dans les prompts livrés avec le dépôt.**
`test_create_project_utilise_un_provider_sans_outils` appelait `create_project`
sans rediriger `settings.ide_prompts_dir` : `_auto_create_missing_agents`
écrivait donc dans le vrai `agents/prompts/`. C'est ce qui recréait
`orchestrateur.md` après chaque suppression, en écrasant son contenu par « un
system prompt d'agent bootstrap ».

Le symptôme — un fichier modifié dans `git status` — était silencieux et
n'était attribué à personne. Une fixture compare désormais l'empreinte du
dossier avant et après chaque test, et nomme le fautif.

## Ce que ça ne fait pas

Un projet dont la suite est **déjà rouge avant le ticket** épuisera ses tours
sans jamais passer. C'est assumé : on n'approuve pas du travail sur une suite
rouge, et le plafond de tours borne le coût.
