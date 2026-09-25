---
id: ticket-170
title: "Lire le diff laisse l'index modifié, et la livraison refuse de rejouer"
type: fix
status: done
pr_number: 18
priority: critical
agent: codeur
depends_on: ["ticket-159", "ticket-166"]
estimated_days: 1
created: 2026-09-25
---

# ticket-170 — Une lecture qui modifie l'index

## Objectif

Qu'une file de tickets s'enchaîne sans qu'un run casse le suivant.

## Contexte

Deux files lancées, deux fois le même arrêt, au même endroit :

```
Pipeline terminé — APPROVED
Livraison interrompue : git rebase main
  error: cannot rebase: You have unstaged changes.
  error: additionally, your index contains uncommitted changes.
ticket-005 : blocked
```

Le ticket suivant trouve alors un arbre sale et se bloque. Une file de trois
tickets en livre donc **un**.

### La cause

`current_diff()` commence par `git add -A -N` — *intent-to-add* — pour que les
fichiers neufs du codeur apparaissent dans le diff soumis au reviewer. C'est
légitime, et la docstring l'explique.

Mais `-N` inscrit **tous** les fichiers non suivis dans l'index, y compris ceux
que `commit_all` exclut ensuite délibérément : les `_preexisting_untracked`, et
`memory/documentation.json` que la documentation écrit (ADR-035). Ces entrées
restent dans l'index après le commit de fin de run.

`git rebase` refuse sur un index non vide. Et `is_clean()` les voit aussi — une
entrée *intent-to-add* est suivie — d'où le blocage du ticket suivant.

Observé : `A memory/documentation.json`, objet vide `e69de29`, jamais commité.

### Pourquoi c'est la troisième fois

Ticket-159 a corrigé un écrit *après* le commit — le déplacement du fichier de
ticket. Celui-ci est un écrit *avant*, qui survit au commit. Même symptôme,
même conséquence, autre mécanisme. Un artefact de build laissé par un
`npm run typecheck` a produit exactement la même panne, ce qui avait fait
conclure à tort à une erreur d'utilisateur.

## Solution proposée

`current_diff()` est une **lecture** : elle rend l'index tel qu'elle l'a trouvé.
Relever les fichiers non suivis avant le `-N`, les retirer de l'index après.
Ceux-là ne peuvent pas avoir été stagés par le codeur — ils étaient non suivis
— donc les remettre dans cet état ne perd rien.

## Critères d'acceptation

- [ ] Après `current_diff()`, l'index ne contient aucune entrée nouvelle
- [ ] Un fichier non suivi le reste après `current_diff()`
- [ ] `current_diff()` rend toujours le contenu des fichiers neufs
- [ ] Ce qui était stagé avant l'appel le reste
- [ ] Rejouer sur une base réussit après un `current_diff()` sur un arbre
      portant un fichier non suivi
- [ ] Sur un dépôt sans commit, l'appel ne lève pas
- [ ] `uv run pytest` et `uv run mypy src/` passent

## Dépendances

ticket-159 et ticket-166, dont ce défaut prolonge la série : la livraison va
un cran plus loin à chaque correction.

## Estimation

Moins d'une journée.

## Risques

Retirer de l'index ce qu'on vient d'y mettre suppose de savoir exactement quoi.
Le relevé est pris **avant** l'ajout, et borné aux fichiers non suivis : rien
de ce que le codeur a stagé lui-même n'entre dans cet ensemble.
