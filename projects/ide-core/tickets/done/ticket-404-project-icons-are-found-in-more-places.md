---
id: ticket-404
title: "Project icons are found in more places, including a Tessera-only icon and the repository icon for ide-core"
type: feat
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: ["ticket-398"]
estimated_days: 0.25
created: 2026-10-12
---

# ticket-404 — Plus d'endroits où trouver l'icône d'un projet

## Objectif

Que chaque projet ait une icône sur sa carte, y compris ceux qui ne sont pas
une application web.

## Contexte

Demande de Benjamin (2026-10-12) : « plus ou moins tous les projets » doivent
avoir une icône cohérente avec le projet. Le ticket-398 ne cherchait que six
chemins sous `frontend/public/` et `public/`. Quatre projets sur quatorze
étaient trouvés. Sont restés sans icône :
- carriere, qui relie pourtant `frontend/public/logo.svg` comme favicon ;
- ide-core, dont l'app est l'IDE lui-même, avec son icône à la racine du
  dépôt ;
- les projets sans interface web : profil GitHub, script, bibliothèque.

## Solution

- `.tessera/icon.svg` est cherché en premier : c'est l'icône que Tessera
  affiche pour un projet sans app, exclue de git par le projet.
- Nouveaux chemins : `frontend/public/logo.svg`, `public/icon.svg`,
  `src/app/icon.svg` et `src/app/icon.png` (Next.js), et `favicon.svg` ou
  `favicon.png` à la racine (pages statiques).
- Un projet `git_root: ancestor` se rabat sur les mêmes chemins à la racine
  du dépôt qui le contient.

## Critères d'acceptation

- [x] Un test de `backend/tests/test_projects_overview.py` vérifie que `.tessera/icon.svg` passe avant un `favicon.svg` racine, et que `src/app/icon.svg`, `favicon.svg` racine et `frontend/public/logo.svg` sont trouvés
- [x] Un test de `backend/tests/test_projects_overview.py` vérifie qu'un projet `git_root: ancestor` reçoit l'icône du dépôt qui le contient, et qu'un projet voisin sans déclaration n'en reçoit aucune
