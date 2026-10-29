---
id: ticket-697
title: "Import project modal split by step"
type: refactor
status: todo
priority: low
agent: codeur
depends_on: [ticket-682]
created: 2026-10-29
---

# ticket-697 — `ImportProjectModal` découpé par étape

## Objectif
Le composant de 383 lignes devient un enchaînement d'étapes qui ont chacune
leur fichier.

## Contexte
`components/Sidebar/ImportProjectModal.tsx` (428 lignes) : cadre de modale,
validation (`validateLocalPath`, `validateGithubUrl`), deux sources, barre de
progression, étapes d'import. Le ticket-682 remplace le cadre de modale et le
gestionnaire `Escape` ; découper avant le ferait deux fois.
`docs/audit/refactos.md` §1.

## Critères d'acceptation
- [ ] Une étape par composant, chacun dans un fichier de moins de 300 lignes ; la validation vit dans un fichier sans JSX
- [ ] L'entrée `components/Sidebar/ImportProjectModal.tsx` disparaît de `PLAFONDS` (ou, si le composant garde l'étape de saisie, y est baissée à 300 ou moins en la retirant)
- [ ] Les tests existants de la modale passent sans changement de leurs attendus
- [ ] `npm run test`, `npx tsc --noEmit` et `npm run lint` passent

## Ce que ça ne fait pas
- Ne change ni le parcours d'import ni les appels API
- Ne touche pas à `CreateProjectModal` (309 lignes : voir ticket-682 d'abord)
