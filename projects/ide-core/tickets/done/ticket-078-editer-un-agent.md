---
id: ticket-078
title: "Éditer le prompt d'un agent, et sortir les projets détachés du dépôt"
type: feat
status: done
pr_number: null
priority: high
agent: codeur
depends_on: [ticket-077]
estimated_days: 1
created: 2026-09-17
---

# ticket-078 — Éditer un agent, détacher hors du dépôt

## Éditer le prompt

Le prompt système décide de tout ce que fait un agent. On pouvait enfin le
**lire** au centre (ticket-076) mais pas le régler : il fallait ouvrir le
fichier dans VSCode juste après l'avoir lu à l'écran.

Une troisième vue — **Rendu / Source / Modifier** — permet de le réécrire.
Un agent **natif** s'ajuste aussi : c'est le premier levier de réglage de
l'IDE, et le refuser n'aurait protégé de rien puisque le fichier reste
éditable à la main. La **suppression** d'un natif, elle, reste interdite :
régler n'est pas effacer.

Un prompt vide est refusé des deux côtés : il priverait l'agent de toute
définition.

## Les projets détachés étaient dans le dépôt de l'IDE

`_detached_destination` calculait `projects/../..`, c'est-à-dire **la racine du
dépôt de vibe-ide**. Un projet retiré y restait, non suivi — un dossier complet,
avec un `.git` incomplet qui ne le protégeait pas : `git rev-parse` y remontait
jusqu'au dépôt de l'IDE.

Le risque était devenu concret avec ADR-028 : depuis qu'un projet peut
travailler dans le dépôt parent, un `git add -A` lancé depuis la racine pouvait
committer le projet détaché en entier. Et « détaché de l'IDE » n'a jamais voulu
dire « déposé dans le dépôt de l'IDE ».

La destination remonte désormais jusqu'au premier dossier hors dépôt. Sur un
workspace ordinaire, sans dépôt au-dessus, rien ne change. Le dossier hérité est
en outre ignoré par git.

## Vérifié

916 tests backend, mypy sur 65 fichiers, 369 tests frontend, 5 flows E2E,
`npm run build`.
