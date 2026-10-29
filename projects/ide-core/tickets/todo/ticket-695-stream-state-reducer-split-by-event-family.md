---
id: ticket-695
title: "Stream state reducer split by event family"
type: refactor
status: todo
priority: low
agent: codeur
depends_on: []
created: 2026-10-29
---

# ticket-695 — Le réducteur de `streamState.ts` par famille d'événements

## Objectif
`appliquerEvenement` cesse d'être un bloc unique : une fonction par famille
d'événements, composées par un aiguillage court.

## Contexte
`hooks/streamState.ts` (627 lignes) : types et état initial (41-240), puis
`appliquerEvenement` (256-627, ≈ 372 lignes) qui traite tous les types
d'événement d'un run. `docs/audit/refactos.md` §2.2. Le rejeu
(`clearTokensForReplay`, `etatDepuisRun`) dépend de ce réducteur.

## Critères d'acceptation
- [ ] `appliquerEvenement` n'est plus qu'un aiguillage ; chaque famille (tokens et outils, étapes, verdicts, file, dialogue…) a sa fonction, dans un fichier de moins de 300 lignes
- [ ] L'entrée `hooks/streamState.ts` de `PLAFONDS` est baissée à 350 ou moins
- [ ] Les tests existants de `streamState` et de rejeu passent sans changement de leurs attendus ; aucune fonction exportée ne change de signature
- [ ] Un test rejoue la même suite d'événements avant et après (fixture commitée) et compare l'état final
- [ ] `npm run test`, `npx tsc --noEmit` et `npm run lint` passent

## Ce que ça ne fait pas
- Ne change ni le format des événements ni le store (ADR-013)
- Ne touche pas à `useSupervision` ni à `useChat`
