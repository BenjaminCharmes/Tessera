---
agent: codeur
created: 2026-10-06
depends_on: []
estimated_days: 0.5
id: ticket-359
pr_number: 284
priority: critical
status: done
title: Tickets created from a plan keep their acceptance criteria
type: fix
---

# ticket-359 — Un ticket créé depuis un plan garde ses critères d'acceptation

## Objectif

Les critères d'acceptation que le planificateur propose arrivent dans le
fichier du ticket, sous `## Critères d'acceptation`, là où le validateur les
cherche.

## Contexte

`PlannerService` rend des `TicketDraftPlan` avec `acceptance_criteria`, et la
modale « Planifier une évolution » les renvoie tels quels à
`POST /projects/{id}/tickets/batch`. Mais `create_tickets_batch`
(`backend/src/tessera/services/ticket_service.py`) construit le `Ticket` avec
`body=draft.description` : les critères sont jetés.

Le 2026-10-05, les 8 tickets du projet `serpent` ont tous été créés ainsi.
Aucun n'a de critère dans son fichier ; le validateur a répondu huit fois
« Aucun critère d'acceptation — approbation automatique » en 0 ms, et les
huit PR ont été mergées sans qu'un seul critère ait été jugé.

## Solution proposée

`create_tickets_batch` écrit le corps à partir de la description **et** des
critères : la description, puis une section `## Critères d'acceptation`
avec une case `- [ ] …` par critère. Le format doit être celui que lit
`_extract_criteria` (`backend/src/tessera/services/pipeline_text.py`).

## Critères d'acceptation

- [ ] Un test crée un lot d'un brouillon portant deux critères et vérifie que le fichier écrit contient `## Critères d'acceptation` suivi de deux lignes `- [ ]`
- [ ] Un test vérifie que `_extract_criteria`, appliqué au corps du ticket ainsi créé, rend exactement les deux critères du brouillon
- [ ] Un brouillon sans critère produit un ticket sans section `## Critères d'acceptation` vide
- [ ] La description du brouillon reste en tête du corps, inchangée

## Ce que ça ne fait pas

- Ne répare pas les tickets déjà créés sans critères.
- Ne change pas ce que fait le validateur face à un ticket sans critère (ticket-360).

## Dépendances

Aucune.

## Risques

Le format du titre de section doit correspondre à `_CRITERIA_HEADING` : le
deuxième critère le vérifie par l'extraction réelle, pas par une chaîne
recopiée.