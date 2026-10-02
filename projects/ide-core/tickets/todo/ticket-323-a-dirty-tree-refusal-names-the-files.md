---
id: ticket-323
title: "A run refused for a dirty tree names the files that block it"
type: fix
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-02
---

# ticket-323 — Un refus pour arbre sale nomme les fichiers en cause

## Objectif

Que l'utilisateur sache quel fichier commiter ou annuler, au lieu de lire
seulement `dirty_working_tree`.

## Contexte

Quand l'arbre n'est pas propre au démarrage, `pipeline_stages.py`
(vers la ligne 65) journalise `dirty_working_tree_refused` et émet
`error` avec `reason="dirty_working_tree"`. Rien ne dit quel fichier gêne.
Le 2026-10-01 et le 2026-10-02, il a fallu chaque fois aller lire `git status`
à la main : un `agents.json` modifié depuis l'écran Agents, un journal du
pipeline resté en attente.

## Solution proposée

- `GitWorkspaceService` expose la liste des fichiers suivis modifiés qui ne
  sont pas de la tenue de livres, celle sur laquelle `is_clean` tranche déjà.
- L'événement `error` porte ces chemins (`fichiers`), et `arret` les nomme
  (« l'arbre contient des modifications hors pipeline : agents.json »).
- La vue du run et le Pipeline log affichent cette phrase.

## Critères d'acceptation

- [ ] Un test sur un dépôt git temporaire vérifie qu'un fichier de code
      modifié apparaît dans la liste, et que le journal du pipeline n'y est
      pas
- [ ] Un test vérifie que l'événement `error` d'un arbre sale porte la liste
      des fichiers
- [ ] Un test du frontend vérifie que le Pipeline log affiche les chemins
      reçus

## Dépendances

Aucune.
