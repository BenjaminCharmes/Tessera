---
id: ticket-776
title: "Design the backend services/ folder grouped by domain"
type: design
status: todo
pr_number: null
priority: low
agent: architect
depends_on: []
estimated_days: 1
created: 2026-11-03
---

# ticket-776 — Concevoir le regroupement de `services/` par domaine

## Objectif

Le dossier `backend/src/tessera/services/` cesse d'être une liste plate où l'on ne retrouve
rien.

## Contexte

`services/` compte 203 modules à plat et trois sous-dossiers seulement (dont
`git_workspace/` et `providers/`). Un comparatif externe du 03/11 le juge « devenu
fourre-tout » et note que `agents/` échappe aux couches vérifiées par le test d'architecture.
Les découpages de la fin octobre (tickets 685-699) ont réduit les gros fichiers mais pas
l'organisation.

## Ce que la conception doit fixer

- Les domaines (par exemple : livraison, file et orchestration, gardes et sécurité,
  documentation, salles et supervision, mise en ligne, projets) et le classement de chaque
  module existant.
- La règle de dépendance entre domaines, vérifiable par le test d'architecture existant.
- Le découpage en tickets de déplacement **à comportement constant**, chacun limité à un
  domaine, et leur ordre pour ne pas bloquer les files en cours (conflits de rebase).
- Le sort de `agents/` dans les couches.

## Critères d'acceptation

- [ ] Une ADR au prochain numéro libre de `projects/ide-core/memory/decisions.md` répond à
      chacun des points ci-dessus, avec la liste complète des modules et leur domaine
- [ ] Les tickets de déplacement sont créés dans `projects/ide-core/tickets/todo/`, chacun
      tient en moins d'une journée
- [ ] Aucun code n'est écrit par ce ticket
