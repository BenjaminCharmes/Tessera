---
id: ticket-135
title: "Reprendre le portfolio : revue, projets récents et section articles"
type: design
status: todo
pr_number: null
priority: medium
agent: architect
depends_on: []
estimated_days: 1
created: 2026-09-23
---

# ticket-135 — Reprendre le portfolio

## Objectif

Remettre le portfolio à jour : une revue de l'existant, les projets récents
dans la section « projets », et une section d'articles.

## Contexte

Le dépôt n'est pas encore importé dans Tessera — il faut le lien avant de
pouvoir en dire quoi que ce soit. La revue est le premier geste, pas la
refonte : on ne sait pas encore dans quel état il est, ni sur quelle stack.

Deux ajouts sont demandés :

- **les projets récents**, Tessera en particulier ;
- **une section d'articles** — avancées, automatisation de processus, mini-lab
  IA local, hébergement de modèles à la maison.

## Solution proposée

1. Importer le dépôt comme projet Tessera. ADR-024 impose que le projet soit
   la racine de son propre dépôt ; ADR-023 met les artefacts en `local` par
   défaut, ce qui est probablement le bon choix ici — un portfolio public n'a
   pas à porter les tickets de sa propre construction.
2. Faire la revue avec le skill `code-review`, et la restituer comme une liste
   de tickets, pas comme un rapport.
3. Décider du format des articles : fichiers Markdown rendus au build, ou
   contenu géré autrement. Ce choix conditionne tout le reste de la section.
4. Arrêter la liste des premiers articles et ce que chacun raconte.

**Point à trancher explicitement** : un portfolio public qui raconte comment
ses projets sont construits dit aussi qu'ils le sont avec des agents. C'est un
choix de communication, et il vaut mieux qu'il soit fait exprès. À noter qu'il
ne change rien à la règle 8 du `CLAUDE.md` — aucune trace d'écriture par IA
dans ce qui est produit —, qui porte sur le code et les commits, pas sur ce
qu'on choisit de raconter dans un article.

## Critères d'acceptation

- [ ] Le dépôt est importé comme projet Tessera et son mode d'artefacts est
      décidé explicitement
- [ ] La revue est restituée sous forme de tickets dans le projet portfolio
- [ ] Le format de la section articles est arrêté
- [ ] La liste des premiers articles est écrite, avec une phrase par article
- [ ] La décision dit ce que le portfolio raconte, ou non, du rôle des agents
- [ ] Aucun ticket d'implémentation n'est créé dans `ide-core`

## Dépendances

Aucune, hors le lien du dépôt.

## Estimation

1 jour pour le cadrage. L'implémentation dépend de ce que la revue trouve.

## Risques

Une revue produit toujours plus de constats qu'on n'en traitera. Le risque est
de transformer « ajouter deux sections » en refonte complète : les tickets de
revue sont à prioriser, pas à exécuter en bloc.
