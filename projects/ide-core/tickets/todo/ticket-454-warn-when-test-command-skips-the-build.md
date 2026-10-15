---
id: ticket-454
title: "A run warns when the project has a build script that its test_command never runs"
type: feat
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-15
---

# ticket-454 — Avertir quand le `test_command` ne lance pas le build

## Objectif

Une erreur qui ne casse qu'au build (bundler, typage du framework, assets)
ne traverse plus toutes les portes du pipeline sans être vue.

## Contexte

make-your-call, 15/10, ticket-007 : le `favicon.ico` généré contenait un PNG
RGB, que Turbopack refuse au build. Testeur, sécurité, reviewer et
validateur ont approuvé, et seule la CI l'a vu (« CI failing », PR #17) :
le `test_command` du projet ne lançait pas `next build`.

Le gabarit (`backend/src/tessera/services/project_from_template.py`) met
déjà `npm --prefix frontend run build` dans son `test_command`. Un projet
importé ou cloné (`backend/src/tessera/services/project_loader.py`) part de
`test_command: null` et sa session l'écrit à la main, sans rien qui
rappelle le build.

## Solution proposée

- Au démarrage d'un run, si le projet (ou un de ses sous-dossiers de
  premier niveau) contient un `package.json` dont `scripts.build` existe, et
  que le `test_command` ne contient ni `build` ni `check:build`, écrire une
  ligne d'avertissement dans `pipeline-log.md` : « test_command ne lance pas
  le build de <dossier> : une erreur de build passera jusqu'à la CI ». Le
  run continue.
- `agents/plugin/skills/mise-en-ligne/SKILL.md` rappelle de mettre le build
  dans le `test_command`.

## Critères d'acceptation

- [ ] Un test vérifie l'avertissement pour un projet dont `package.json`
      déclare `scripts.build` et dont le `test_command` vaut `npm test`
- [ ] Un test vérifie l'absence d'avertissement quand le `test_command`
      contient `run build`
- [ ] Un test vérifie l'absence d'avertissement sans `package.json`
- [ ] `agents/plugin/skills/mise-en-ligne/SKILL.md` contient une ligne qui
      demande le build dans le `test_command`

## Ce que ça ne fait pas

- Ne modifie le `test_command` d'aucun projet (`agents.json` est hors
  d'atteinte des agents).
