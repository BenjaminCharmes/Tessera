---
id: ticket-072
title: "Committer sur un projet aux artefacts locaux, et montrer ce que dit le reviewer"
type: fix
status: done
pr_number: null
priority: critical
agent: codeur
depends_on: [ticket-071]
estimated_days: 1
created: 2026-09-17
---

# ticket-072 — Le commit échouait sur tout projet aux artefacts locaux

## Ce qui s'est passé

Run réel sur `tmp`, trois tours complets — codeur et reviewer, six appels
d'agents, **1,98 $** — puis :

```
Erreur : le commit de fin de run a échoué : le travail est resté dans l'arbre
git add -A -- . :(exclude)tickets/ :(exclude)memory/pipeline-log.md
The following paths are ignored by one of your .gitignore files: memory tickets
```

## La cause

Deux décisions à moi se contredisaient.

ADR-021 met `tickets/` et `memory/` dans `.git/info/exclude` quand un projet
est en mode artefacts **local**. ADR-018 fait passer `commit_all` par des
pathspecs `:(exclude)tickets/` pour tenir la tenue de livres à l'écart du
commit de ticket.

Or **nommer un chemin déjà ignoré dans un pathspec fait sortir `git add` en
code 1**, alors que la même commande sans ce pathspec réussit et saute le
chemin en silence. Vérifié en isolation :

```
git add -A -- .                                   # code 0, ne stage que le code
git add -A -- . ':(exclude)tickets/'              # code 1
```

Donc : sur **tout** projet aux artefacts locaux — c'est-à-dire tout projet
importé ou cloné depuis ADR-023, donc tous les projets clients — aucun run ne
pouvait committer.

## Ce qui a bien fonctionné

Cette panne existait avant. Elle était invisible : `commit_failed` partait en
`warning` et le run annonçait APPROVED. C'est **ticket-068** qui l'a rendue
bruyante, avec la sortie git complète à l'écran — de quoi diagnostiquer en une
lecture. Le correctif d'hier a fait exactement son travail.

## Décision

Les `:(exclude)` ne sont posés que sur les chemins **que le dépôt n'ignore pas
déjà**, et la tenue de livres n'est pas commitée quand elle est exclue : un
chemin ignoré est hors du dépôt par décision, pas par accident.

## En marge : la revue était tronquée

`parseVerdict` ne gardait que `lines[0]`. Le reviewer annonçait « voici ma
review » et l'utilisateur ne voyait rien de plus — alors que le détail est la
seule chose qui permette de juger. Il est désormais dépliable.

Et le bouton d'arrêt prenait toute la largeur sur deux lignes ; il est réduit,
l'explication passe en infobulle.

## Vérifié

893 tests backend, mypy sur 65 fichiers, 337 tests frontend, 5 flows E2E,
`npm run build`.
