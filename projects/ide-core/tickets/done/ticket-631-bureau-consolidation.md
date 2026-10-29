---
agent: codeur
created: 2026-10-28
depends_on:
- ticket-630
estimated_days: 1
id: ticket-631
plan: true
pr_number: null
priority: medium
status: done
title: 'Bureau consolidation: one wall component and one sprite scale'
type: refactor
---

# ticket-631 — Consolider le Bureau : un seul mur, une seule échelle

## Objectif
Qu'après une vingtaine de tickets sur le Bureau, ses salles et ses pièces se
dessinent avec les mêmes briques, à la même échelle.

## Contexte
Le Bureau s'est construit par petits tickets (564 à 630). Deux écarts relevés le 28/10 :
- `Salle.tsx` (salles du haut) et `FondDeLaPiece.tsx` (pièces des projets)
  dessinent chacun leurs fenêtres, leurs plafonniers et leur interrupteur, avec
  leur propre mise en page ;
- l'interrupteur (`design/bureau/Interrupteur.tsx`) ne passe pas par `Agrandi` :
  il garde ses pixels bruts quand tout le reste suit `useEchelleDesSprites`.
  Il paraît donc plus petit à 1920 qu'à 1536.

Le reviewer et le validateur ne lisent qu'un diff : ils ne voient pas une
duplication entre deux fichiers que le diff ne touche pas.

## Solution proposée
- Un composant de mur partagé dessine fenêtres, plafonniers et interrupteur pour
  `Salle.tsx` et pour `FondDeLaPiece.tsx`.
- Tout sprite passe par `Agrandi` : l'interrupteur y entre, avec une grille réduite
  pour garder sa taille à 1536.
- Le tour de plan relève les autres doublons de `components/BureauView/`, `lib/bureau/`
  et `design/bureau/`, et le rapport du codeur les liste, traités ou non.

## Critères d'acceptation
- [ ] `Salle.tsx` et `FondDeLaPiece.tsx` dessinent fenêtres, plafonniers et interrupteur par un même composant, qui n'existe qu'une fois
- [ ] Un test rend une `Piece` et une `Salle` et vérifie que chaque élément `[data-sprite]` se trouve dans un élément `[data-agrandi]`
- [ ] `BoutonLumiere.tsx` rend `Interrupteur` dans `Agrandi`

## Ce que ça ne fait pas
- Ne change aucun comportement visible, hors la taille de l'interrupteur à 1920.