---
id: ticket-663
title: "The folder pile shrinks to the furniture's scale, and ceiling lights cast a fading cone"
type: fix
status: done
pr_number: null
priority: low
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-10-28
---

# ticket-663 — Une pile de dossiers à l'échelle, et des cônes de lumière

## Objectif
Accorder la pile de dossiers et la lumière des plafonniers au reste du Bureau.

## Contexte
Retours du 28/10 :
- la pile de dossiers paraissait énorme à côté des meubles, une fois ceux-ci réduits ;
- le halo des plafonniers était une ellipse autour de la lampe ; Benjamin le
  voulait conique vers le bas, plus large, et plus estompé en journée.

## Solution proposée
- `Dossier` passe de 30 × 24 à 20 × 16 px, et la pile se resserre.
- `CeilingLamp` dessine un cône qui s'élargit vers le bas et s'efface par un
  dégradé ; `jour` le rend plus pâle. Le jeton `--sprite-halo` laisse place à
  `--sprite-halo-coeur`.

## Critères d'acceptation
- [x] `Dossier.tsx` dessine 20 × 16 px
- [x] `CeilingLamp.tsx` dessine un polygone en dégradé, plus pâle quand `jour` est vrai
- [x] Captures relues : la pile tient sur l'imprimante, le cône descend et s'efface

## Ce que ça ne fait pas
- Ne change pas le moment où la lumière s'allume.
