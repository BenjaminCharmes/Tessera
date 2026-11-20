---
id: ticket-777
title: "A back-row agent stands on the floor, in front of the furniture"
type: fix
status: done
pr_number: null
priority: low
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-11-04
---

# ticket-777 — Un agent du fond se tient sur le sol, devant le meuble

## Objectif

Un agent à la machine à café ou à la porte a les pieds au sol, devant le meuble, pas au-dessus
de sa base.

## Contexte

Relevé par Benjamin le 04/11 : à la machine à café, les pieds de l'agent sont plus hauts que
le meuble devant lequel il se tient. `DENIVELE_DU_FOND` valait 132 px en dur
(`frontend/src/components/BureauView/AgentsDeLaPiece.tsx`) : les pieds tombaient à 160 px du
bas, au ras du mur, alors que les meubles du fond descendent de 4 px sous le mur (`-bottom-1`
de `Pose`, ticket-727). Mesuré dans le navigateur à 1280, 1536 et 1920 px : sol de 160 px sous
le mur, base des meubles à 156 px.

## Solution

Le dénivelé se déduit du sol de la pièce (`h-40` de `Piece`), de l'enfoncement des meubles et
d'un pas devant le meuble : 160 − 4 − 4 − 28 = 124 px. Retouche faite à la main.

## Critères d'acceptation

- [x] `AgentsDeLaPiece.test.tsx` vérifie qu'un agent du fond a les pieds sous la base des
      meubles du fond (156 px), et qu'un agent de la rangée reste à 28 px
