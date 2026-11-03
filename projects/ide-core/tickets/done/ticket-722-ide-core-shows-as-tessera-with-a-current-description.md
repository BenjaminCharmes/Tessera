---
id: ticket-722
title: "ide-core shows as Tessera, with a current description"
type: docs
status: done
pr_number: null
priority: low
agent: codeur
depends_on: []
estimated_days: 0.1
created: 2026-10-30
---

# ticket-722 — ide-core s'affiche comme Tessera, avec une description à jour

## Objectif
Le projet bootstrap s'affiche « Tessera — l'IDE qui se construit lui-même » dans la
liste des projets, avec une description qui dit ce que fait l'IDE aujourd'hui.

**Ce ticket autorise la modification de `projects/ide-core/CLAUDE.md`** (règle 5),
limitée à son titre. Fait à la main.

## Contexte
Revue des noms de projets du 30/10, demandée par Benjamin : les titres suivent
le format « Nom — sous-titre », et le projet s'affichait « ide-core ». Sa
description venait du premier paragraphe du `CLAUDE.md` (« Projet bootstrap…
pour rendre l'IDE opérationnel »), dépassée.

## Fait
- Titre du `CLAUDE.md` changé ; le dossier et l'identifiant restent `ide-core`.
- `description` déclarée dans `agents.json`, qui l'emporte sur le `CLAUDE.md` (ticket-399).

## Critères d'acceptation
- [x] `GET /api/v1/projects/overview` rend pour `ide-core` le nouveau nom et la nouvelle description
