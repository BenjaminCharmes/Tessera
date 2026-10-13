---
agent: codeur
created: 2026-10-13
depends_on: []
estimated_days: 0.5
id: ticket-410
pr_number: null
priority: medium
status: done
title: The projects overview tells, for each project, whether it declares services
  and whether they are running
type: feat
---

# ticket-410 — La vue d'ensemble des projets porte l'état de leurs services

## Objectif

Que chaque carte de la vue Projets sache, sans requête de plus, si son
projet a une app à lancer et si elle tourne déjà.

## Contexte

Benjamin veut démarrer plusieurs projets d'affilée depuis la vue Projets
(2026-10-13). Aujourd'hui, cliquer une carte ouvre les tickets du projet ;
le bouton de services n'existe que dans l'en-tête du projet actif. Le
ticket-411 mettra ce bouton sur chaque carte. Interroger
`GET /projects/{id}/services` pour quinze cartes ferait quinze requêtes : la
vue d'ensemble (`GET /api/v1/projects/overview`, ticket-398) est faite pour
tout porter en une.

## Solution proposée

- `ProjectOverview` (`services/project_overview.py`) gagne
  `services_declares: bool` et `services_en_cours: bool`.
- `get_projects_overview` (`routers/projects.py`) les calcule **hors du
  cache** de `build_overview`, comme `run_actif` : `load_services_config`
  sur la racine du projet pour le premier, `PROCESS_REGISTRY` pour le second
  (au moins un service du projet vivant).
- Type `ProjectOverview` de `frontend/src/types/api.ts` mis à jour.

## Critères d'acceptation

- [ ] Un test vérifie que `services_declares` vaut `true` pour un projet dont
      `agents.json` déclare `services`, et `false` sinon
- [ ] Un test vérifie que `services_en_cours` vaut `true` quand le registre de
      processus a un service vivant pour ce projet, `false` sinon
- [ ] Un test vérifie que `services_en_cours` change entre deux appels sans
      que rien d'autre du projet ne change (pas figé par le cache)
- [ ] `frontend/src/types/api.ts` déclare les deux champs sur `ProjectOverview`

## Dépendances

Aucune. Le ticket-411 en dépend.