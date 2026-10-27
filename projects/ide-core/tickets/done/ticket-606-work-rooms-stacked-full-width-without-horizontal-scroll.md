---
agent: codeur
created: 2026-10-27
depends_on: []
estimated_days: 0.5
id: ticket-606
pr_number: 685
priority: high
status: done
title: Work rooms stack one per row and fill the view's width, without a horizontal
  scroll
type: feat
---

# ticket-606 — Les salles de travail s'empilent, en pleine largeur, sans défilement horizontal

## Objectif

Qu'on voie chaque salle de travail **en entier**, sans faire défiler : une
salle par ligne, sur toute la largeur de la vue.

## Contexte

Retour de Benjamin le 27/10 en regardant le Bureau : « on peut scroller
horizontalement dans les salles de travail par projet, du coup on ne voit pas
toute la salle ». Aujourd'hui :

- `components/BureauView/index.tsx` range les salles en `grid grid-cols-2` :
  deux salles côte à côte, chacune trop étroite pour son sol ;
- `components/BureauView/Piece.tsx` pose le sol dans un `overflow-x-auto`
  autour d'un bloc `w-200` (800 px), celui de la maquette ;
- tout le placement des agents est calculé en pixels sur ce sol de 800 px :
  `lib/bureau/activites.ts` (`MACHINE_X`, `PORTE_X`, les centres des postes),
  appliqué par `translate(${x}px, …)` dans `AgentsDeLaPiece.tsx`.

Élargir le sol en CSS (`w-full`) décalerait donc les agents de leurs bureaux.

## Solution proposée

1. **Empiler** : dans `index.tsx`, les salles en mode pièces passent en une
   colonne (`flex flex-col`), comme le mode compact.
2. **Mettre le sol à l'échelle plutôt que l'élargir** : le sol garde son
   repère logique de 800 px — rien ne change dans `activites.ts` — et il est
   rendu agrandi ou réduit pour remplir la largeur de la salle. Une fonction
   pure `echelleDuSol(largeurDisponible: number): number` dans
   `lib/bureau/` donne le facteur (`largeur / 800`, borné entre 0,5 et 2 pour
   que les sprites ne deviennent ni minuscules ni énormes) ; un
   `ResizeObserver` sur le conteneur l'applique (`transform: scale` avec
   `transform-origin: top left` et la hauteur compensée, ou `zoom`, au choix du
   codeur). Au-delà de la borne haute, le sol se centre.
3. Supprimer l'`overflow-x-auto` du sol dans `Piece.tsx`.

Le mobilier pixel art supporte l'agrandissement : garder
`image-rendering: pixelated` / `shape-rendering: crispEdges` s'ils sont déjà
posés sur les SVG.

## Critères d'acceptation

- [ ] `components/BureauView/index.tsx` ne contient plus `grid-cols-2` : en mode pièces, les salles sont rendues dans un conteneur en une colonne.
- [ ] `components/BureauView/Piece.tsx` ne contient plus `overflow-x-auto` pour le sol.
- [ ] `lib/bureau/echelleDuSol.ts` exporte `echelleDuSol`, et un test vérifie : 800 → 1, 1200 → 1,5, 300 → 0,5 (borne basse), 2400 → 2 (borne haute).
- [ ] Un test de `Piece.test.tsx` vérifie que le sol n'est plus dans un conteneur à défilement horizontal (le test qui attendait `w-200` sous `.overflow-x-auto` est remplacé, pas supprimé).
- [ ] `lib/bureau/activites.ts` n'est pas modifié par le diff : les positions des agents restent dans le repère de 800 px.

## Dépendances

Aucune. Les tickets 601 à 603 qui suivent dans la file bâtissent sur ce sol.

## Estimation

Une demi-journée.

## Risques

- Un `transform: scale` ne change pas la place occupée dans le flux : sans
  hauteur compensée, la salle suivante chevauche. `zoom` n'a pas ce défaut.
- Les infobulles portées (ticket-593) sont en portail : elles ne doivent pas
  hériter de l'échelle.