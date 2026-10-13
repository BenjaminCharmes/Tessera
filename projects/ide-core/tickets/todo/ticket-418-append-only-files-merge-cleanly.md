---
id: ticket-418
title: "Append-only pipeline files no longer stop a delivery on a rebase conflict"
type: fix
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-13
---

# ticket-418 — Les fichiers en ajout seul ne bloquent plus une livraison

## Objectif

Qu'un conflit de rebase sur `memory/pipeline-log.md` ou
`memory/documentation.json` — deux fichiers où chaque run ne fait
qu'ajouter — ne stoppe plus jamais une livraison.

## Contexte

Le 2026-10-13, la livraison du ticket-009 de `curio` s'est arrêtée sur
« Conflit avec main sur : memory/pipeline-log.md », puis le rebase manuel a
buté sur `memory/documentation.json` (deux tickets ajoutant chacun leur id
à la même liste). Déjà relevé le 2026-10-06 sur les projets lancés ce
jour-là. Le résolveur de conflit (ADR-033) n'est pas le bon outil pour ça :
la résolution est mécanique.

## Solution proposée

- `pipeline-log.md` : déclarer `memory/pipeline-log.md merge=union` — le
  pilote d'union est natif à git — dans `.git/info/attributes` du dépôt du
  projet (comme ADR-021 le fait pour `.git/info/exclude` : rien dans le
  dépôt du client), posé par le service qui prépare l'espace git avant un
  run.
- `documentation.json` : pendant un rebase de livraison, si le seul conflit
  porte sur ce fichier, le résoudre en prenant l'union des listes d'ids
  (JSON relu et réécrit), puis poursuivre ; sinon comportement inchangé.

## Critères d'acceptation

- [ ] Un test vérifie que l'espace git d'un projet porte
      `memory/pipeline-log.md merge=union` dans `.git/info/attributes`
      après préparation, sans doublon si on prépare deux fois
- [ ] Un test (deux branches qui ajoutent chacune une ligne au journal)
      vérifie que le rebase de livraison réussit et garde les deux lignes
- [ ] Un test vérifie qu'un conflit limité à `documentation.json` se résout
      par union des ids et que la livraison continue
- [ ] Un test vérifie qu'un conflit sur un autre fichier garde le
      comportement actuel (arrêt, branche intacte)

## Dépendances

Aucune.
