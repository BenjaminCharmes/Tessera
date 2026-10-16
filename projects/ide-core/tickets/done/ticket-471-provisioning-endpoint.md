---
agent: codeur
created: 2026-10-16
depends_on:
- ticket-465
estimated_days: 1
id: ticket-471
priority: medium
status: done
title: A project is put online by an explicit request, and its per-step state can
  be read without writing anything
type: feat
---

# ticket-471 — Endpoint de mise en ligne

## Objectif

Le seul point d'entrée de la mise en ligne : une requête explicite de
l'utilisateur lance le plan, une lecture en rend l'état sans rien écrire.

## Contexte

ADR-053 : seule une action de l'utilisateur déclenche la mise en ligne, jamais
un agent du pipeline. Le plan et les étapes viennent des tickets 465 à 470 ;
l'endpoint construit le plan d'après `online.resources`. Il suit
`POST /orchestrator/run` + `WS /orchestrator/observe` (ADR-041) : on lance en
HTTP, on suit sur la WebSocket. Le routeur est celui des projets (auth
`STATIC_TOKEN` incluse).

## Solution proposée

- `POST /api/v1/projects/{project_id}/provision` : 202, lance
  `ProvisioningPlan.run` en tâche de fond ; 404 projet inconnu ; 422 sans bloc
  `online` ; 409 si une mise en ligne du projet tourne déjà (verrou propre à
  la mise en ligne, distinct de `RunLock`).
- `GET /api/v1/projects/{project_id}/provision` : `run(dry_run=True)` — chaque
  étape `inspect`, aucune `apply` — et rend la liste `{step, state, detail}`.
- Une exception d'étape devient un événement `failed` et libère le verrou ; la
  réponse ne porte aucune trace d'appel.
- Aucun module du pipeline, du chat ni des agents n'importe
  `services/provisioning`.

## Critères d'acceptation

- [ ] Un test vérifie que `POST` rend 202 et déclenche le plan, 404 pour un
      projet inconnu et 422 pour un projet sans bloc `online`
- [ ] Un test vérifie qu'un second `POST` pendant une mise en ligne rend 409,
      et que le verrou est libéré après un échec d'étape
- [ ] Un test vérifie que `GET` n'appelle que `inspect` et rend l'état par étape
- [ ] Un test vérifie qu'une exception d'étape devient un événement `failed` et
      que la réponse HTTP ne contient ni trace d'appel ni valeur de jeton
- [ ] Un test vérifie, par analyse des imports, qu'aucun module de
      l'orchestrateur, du chat ni des agents n'importe `services.provisioning`
- [ ] Un test vérifie qu'avec `STATIC_TOKEN` renseigné les deux routes exigent
      `Authorization: Bearer`

## Ce que ça ne fait pas

N'ajoute aucun écran (ticket-472). N'expose aucune route de suppression.

## Dépendances

ticket-465. Une mise en ligne utile attend au moins le ticket-466.