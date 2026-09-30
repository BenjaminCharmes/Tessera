---
id: ticket-269
title: "Opening a PR from the IDE targets the project's declared base branch"
type: fix
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-09-30
---

# ticket-269 — « Ouvrir la PR » vise la branche de base du projet

## Objectif

Qu'une PR ouverte depuis l'IDE sur un projet vise la branche que ce projet
déclare, comme le fait déjà la livraison.

## Contexte

Constaté le 2026-09-30 sur `carriere-app` et `freelance`, qui déclarent
`"base_branch": "main"` et n'ont pas de `develop`.

- La livraison lit la base du projet : `routers/orchestrator.py` prend
  `politique.base_branch`, puis retombe sur `settings.github_base_branch`.
- L'ouverture manuelle, `POST /{project_id}/tickets/{ticket_id}/open-pr`
  (`routers/tickets.py`), passe **toujours** `settings.github_base_branch`
  (`develop`) — et une seconde route du même fichier fait de même. Sur ces
  projets, la PR viserait une branche inexistante.

## Solution proposée

- Une seule fonction résout la base d'un projet — `base_branch` de sa
  politique, sinon `settings.github_base_branch` — et les trois appelants
  l'utilisent. Ne pas recopier la règle (ADR-034).

## Critères d'acceptation

- [ ] Un test montre que `open-pr` sur un projet déclarant
      `"base_branch": "main"` passe `main` comme base.
- [ ] Un test montre que `open-pr` sur un projet sans `base_branch` passe
      `settings.github_base_branch`.
- [ ] Le diff ne contient plus `base_branch=settings.github_base_branch` dans
      `routers/tickets.py`.

## Dépendances

Aucune.

## Estimation

Une demi-journée. Backend uniquement.

## Risques

Aucun sur ide-core, qui ne déclare pas de `base_branch` et garde `develop`.
