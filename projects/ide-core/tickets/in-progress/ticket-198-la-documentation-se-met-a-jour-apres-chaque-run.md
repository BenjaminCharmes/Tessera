---
id: ticket-198
title: "La documentation se met à jour à la fin de chaque run, pas seulement d'une file"
type: feat
status: in-progress
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-26
---

# ticket-198 — La documentation se met à jour à la fin de chaque run, pas seulement d'une file

## Objectif

Qu'après un run approuvé, quel que soit le mode, `doc-technique` et
`doc-fonctionnelle` mettent à jour `README.md`, `docs/architecture.md` et
`docs/guide-utilisateur.md` avec ce qui vient d'être livré.

## Contexte

Les deux agents existent (ADR-035) et travaillent par lot : ils reçoivent
les tickets livrés depuis le marqueur `memory/documentation.json`, rendent
des modifications ciblées, et sont appelés par `_documenter_le_lot` à la fin
d'une **file** et d'un run **autonome** seulement. Un run simple, le mode le
plus utilisé depuis l'IDE, ne déclenche jamais rien : les tickets
s'accumulent derrière le marqueur jusqu'à ce qu'une file finisse, et la
documentation décrit un produit en retard de plusieurs livraisons.

ADR-035 refuse la documentation **par ticket** parce que trois tickets d'une
même feature réécrivaient trois fois le même fichier. Ce n'est pas ce que
fait un déclenchement en fin de run simple : le lot reste défini par le
marqueur, donc un run simple qui suit une file de cinq tickets documente
les six d'un coup, et une file continue de documenter une fois à sa fin.

Depuis le ticket-189, les deux rôles tournent sur Ollama avec repli : le
coût du déclenchement supplémentaire est nul sur la machine équipée.

## Solution proposée

- `run_pipeline` (mode simple) appelle `_documenter_le_lot` après la
  livraison d'un run **approuvé**, comme le font la file et le run
  autonome. Un run non approuvé ne documente rien : il n'a rien livré.
- Le lot se documente **sur la branche du run**, avant sa livraison, pour
  que les modifications de documentation partent dans la même PR que le
  code qu'elles décrivent — c'est ce qui fait qu'elles sont relues. Vérifier
  ce que fait la file aujourd'hui (elle documente après la livraison du
  dernier ticket) et aligner : si la documentation est commitée à part,
  dire où, et ne jamais laisser l'arbre sale (ADR-018).
- Un échec de documentation ne fait jamais échouer le run (même régime
  qu'ADR-030 pour la livraison) : il part dans un événement `doc_updated`
  avec les refus, lisible à l'écran.
- ADR-035 est amendé d'une ligne : « à la fin de chaque run approuvé, en
  lot depuis le marqueur ».

## Critères d'acceptation

- [ ] Un test vérifie qu'un run simple approuvé appelle `documenter` une fois
- [ ] Un test vérifie qu'un run simple non approuvé n'appelle pas `documenter`
- [ ] Un test vérifie qu'une file appelle `documenter` après chacun de ses
      tickets approuvés, et plus rien à sa fin (la fin de file laissait la
      documentation sur le disque, sans commit)
- [ ] Un test vérifie qu'en `git_root: ancestor` les éditions s'appliquent à
      la racine du dépôt, où vivent `README.md` et `docs/`
- [ ] Un test vérifie qu'une exception dans `documenter` ne change pas le
      résultat du run
- [ ] Après un run simple, l'arbre est propre : la documentation est commitée
      (test sur le double git)
- [ ] ADR-035 porte l'amendement, sous son budget de mots
- [ ] `uv run pytest` et `uv run mypy src/` passent

## Ce que ça ne fait pas

Ne change ni les prompts ni le format des modifications. Ne documente pas
depuis le chat. Ne touche pas au périmètre `README.md` + `docs/`.

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

Un run simple documente désormais aussi les tickets livrés à la main ou par
une file interrompue : c'est voulu, le marqueur est la seule frontière.
