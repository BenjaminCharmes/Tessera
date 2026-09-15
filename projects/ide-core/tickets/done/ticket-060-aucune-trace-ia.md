---
id: ticket-060
title: "Aucune trace d'écriture par IA dans ce que produit l'IDE"
type: chore
status: done
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-15
---

# ticket-060 — Aucune trace d'écriture par IA

## Objectif

Ce que vibe-ide écrit dans le dépôt d'un utilisateur ne doit porter aucune
mention d'un outil d'IA.

## Contexte

Les commits, descriptions de PR et fichiers produits par vibe-ide atterrissent
dans le dépôt de l'utilisateur — **et parfois dans celui d'un client**. La
provenance du code n'y a pas sa place : c'est le travail de l'utilisateur, sous
sa responsabilité, dans son dépôt.

Le skill `ticket-workflow` prescrivait jusqu'ici une ligne
`Co-Authored-By: Claude …` dans chaque message de commit, et les descriptions
de PR portaient une mention « Generated with Claude Code ».

## Périmètre

Aucune mention d'assistant, sous aucune forme :

- messages de commit (`Co-Authored-By`, corps, sujet)
- titres et descriptions de PR
- commentaires de code et docstrings
- fichiers générés (tickets, ADR, documentation)
- messages d'erreur et logs

## Solution livrée

1. Le skill `ticket-workflow` interdit explicitement toute attribution, au lieu
   de la prescrire.
2. `CLAUDE.md` en fait une règle du dépôt — elle s'applique donc aussi aux
   agents du pipeline, qui lisent ce fichier.
3. Le prompt du `codeur` et celui du `chat` rappellent la contrainte, puisque
   ce sont eux qui écrivent dans les dépôts.

## Contrainte

Ce ticket **autorise la modification de `CLAUDE.md`** (règle 5).

## Critères d'acceptation

- [x] Le skill `ticket-workflow` interdit l'attribution
- [x] `CLAUDE.md` porte la règle, dans la section Git et dans les règles agents
- [x] Les prompts `codeur` et `chat` la rappellent
- [x] Aucun fichier du dépôt ne prescrit plus d'attribution

## Historique existant

**56 des 177 commits du dépôt portent déjà `Co-Authored-By: Claude`.** Les
réécrire suppose de réécrire l'historique publié de `main` et `develop` — une
opération destructive qui n'est pas prise ici sans décision explicite.

## Dépendances

Aucune.

## Estimation

**1j**.
