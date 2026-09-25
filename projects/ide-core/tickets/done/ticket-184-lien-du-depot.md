---
id: ticket-184
title: "Le dépôt GitHub d'un projet s'ouvre d'un clic"
type: fix
status: done
pr_number: 46
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-25
---

## Le problème

Le panneau Versionnement affiche l'adresse du dépôt distant comme du texte :
elle se lit, elle ne s'ouvre pas.

En cherchant où la rendre cliquable, un défaut plus net est apparu. La sidebar
porte déjà un lien « GH », et il est cassé : `href={project.github_remote}`,
alors que cette clef vaut `owner/repo` — c'est ce que `GitHubService`
concatène dans `/repos/{repo}/issues`. Le navigateur la résout donc contre
l'origine de l'app, et le lien mène à une page de l'IDE.

## Ce qu'il faut faire

Une fonction unique qui rend l'URL navigable d'un dépôt, ou `null` quand elle
ne peut pas conclure, et les deux affichages s'en servent :

- `owner/repo` — la forme d'`agents.json` — devient une URL GitHub
- une URL `https://` se garde, son `.git` final en moins
- une adresse SSH (`git@hôte:owner/repo.git`) devient `https://hôte/owner/repo`
- tout le reste rend `null` : pas de lien plutôt qu'un lien qui ment

## Ce que ça ne fait pas

Aucune vérification que le dépôt existe ou qu'il est accessible : un lien mort
reste possible, il mène au moins là où il prétend. `owner/repo` suppose GitHub,
faute d'hôte déclaré — les autres formes, elles, gardent le leur.
