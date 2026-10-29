---
id: ticket-692
title: "Documentation module split into edits, selection and service"
type: refactor
status: todo
priority: low
agent: codeur
depends_on: []
created: 2026-10-29
---

# ticket-692 — `documentation.py` : éditions, sélection et service à part

## Objectif
Les fonctions pures d'édition Markdown et de sélection des tickets quittent le
module du service.

## Contexte
`services/documentation.py` (714 lignes) : application d'éditions
(`appliquer_editions`, `_localiser`, `_inserer`, `_remplacer` : 89-283, pures),
sélection des tickets à documenter (284-372), puis `DocumentationService` et la
composition du brief (373-714, dont `mettre_a_jour` : 131 lignes).
`docs/audit/refactos.md` §1.

## Critères d'acceptation
- [ ] Les fonctions d'édition et de sélection vivent dans deux modules de moins de 300 lignes chacun ; `grep -n "def appliquer_editions" backend/src` ne rend que le module d'édition
- [ ] L'entrée de `services/documentation.py` dans `PLAFONDS` est baissée à 450 ou moins
- [ ] Les tests d'édition et de sélection passent sans changement de leurs attendus ; seule une cible d'import ou de `patch` change
- [ ] La règle « une édition cite le code livré » (ADR-057) n'est pas touchée : le diff ne modifie aucune ligne de `_brief` ni de `_contenu_documentable`, sauf leur déplacement
- [ ] `uv run pytest` et `uv run mypy` passent

## Ce que ça ne fait pas
- Ne découpe pas `mettre_a_jour` en étapes (à faire si le module reste au-dessus de 300)
- Ne change aucun brief ni aucune règle d'édition
