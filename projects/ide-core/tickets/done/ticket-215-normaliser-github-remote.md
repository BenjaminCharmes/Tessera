---
agent: codeur
created: 2026-09-28
depends_on: []
estimated_days: 1
id: ticket-215
pr_number: null
priority: high
status: done
title: github_remote se normalise en propriétaire/dépôt, quelle que soit sa forme
type: fix
---

# ticket-215 — Normaliser `github_remote`

## Objectif

Un `github_remote` écrit en forme courte (`owner/repo`), en URL HTTPS (avec ou sans `.git`) ou en SSH est compris de la même façon par la livraison et par l'interface.

## Contexte

Personne ne normalise la valeur lue dans `agents.json`, et deux consommateurs attendent deux formes différentes :

- `GitHubService` construit `repos/{repo}/…` avec la valeur brute. Il lui faut donc `owner/repo`. Avec une URL, l'appel vise `repos/https://github.com/…` et échoue.
- `nom_de_la_forge` attend une URL. Avec `BenjaminCharmes/Tessera`, il prend `benjamincharmes` pour l'hôte, et l'interface affiche « Dépôt hébergé sur benjamincharmes : l'ouverture de pull request n'est pas automatisée ici ». C'est faux : la livraison de ce projet ouvre bien ses PR.

`git_link` et `git_clone`, qui sont l'action « lier un dépôt » de l'IDE, écrivent la forme URL. La plupart des projets personnels l'ont donc, et leur livraison automatique échouerait à l'ouverture de la PR.

## Solution proposée

Une fonction unique qui rend `(forge, owner/repo)` à partir de n'importe quelle forme, appelée par `_load_github_remote`. `Project.github_remote` porte alors toujours `owner/repo`, et la forge devient un champ à part. Une forme courte sans hôte veut dire GitHub.

## Critères d'acceptation

- [ ] Un test : `BenjaminCharmes/Tessera`, `https://github.com/BenjaminCharmes/Tessera`, `https://github.com/BenjaminCharmes/Tessera.git` et `git@github.com:BenjaminCharmes/Tessera.git` donnent tous `BenjaminCharmes/Tessera` et la forge GitHub
- [ ] Un test : `https://gitlab.com/a/b` donne la forge GitLab, et `forge_supportee` rend faux
- [ ] Un test : `GitHubService` construit avec un remote en forme URL appelle `repos/owner/repo/…`
- [ ] `GET /api/v1/projects/{id}/tickets/{ticket}/activity` rend `pr_supported: true` pour un remote en forme courte
- [ ] Les `agents.json` existants ne sont pas réécrits

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

Un remote GitHub Enterprise (autre hôte) ne doit pas passer pour github.com. La forge vient de l'hôte, et seule une forme sans hôte est présumée GitHub.