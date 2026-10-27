---
agent: codeur
created: 2026-10-27
depends_on: []
estimated_days: 0.25
id: ticket-607
pr_number: null
priority: medium
status: done
title: 'Agents'' hair reads as hair: it frames the face, and the bun sits against
  the head'
type: fix
---

# ticket-607 — Les cheveux des agents se lisent comme des cheveux

## Objectif

Qu'un agent du Bureau ait une tête lisible : des cheveux qui encadrent le
visage, pas un objet posé dessus.

## Contexte

Benjamin, le 27/10, sur une capture d'un agent assis : « pourquoi ils ont un
truc bizarre sur la tête ? ». Dans `design/bureau/Tete.tsx` :

- la coiffure `court` (et `chignon`) n'est qu'une bande de 6 × 2 posée
  au-dessus du visage, sans rien sur les côtés : à la taille réelle, elle se
  lit comme un bonnet ou un casque ;
- le `chignon` ajoute un rectangle de 2 × 1 au sommet de cette bande : un
  pixel isolé qui se lit comme une antenne ou un pompon.

## Solution proposée

Dans `Tete.tsx` uniquement, qui sert aux deux poses :

- `court` et `chignon` : la bande du dessus descend d'une unité sur chaque
  tempe (un rect de 1 × 1 à gauche et à droite du visage, sur sa première
  ligne), pour encadrer le visage ;
- `chignon` : le chignon devient un chignon — au moins 4 unités de large et
  2 de haut, collé à la bande sans espace, centré sur la tête ;
- `long` et `chauve` ne changent pas.

Vérifier le rendu à la taille réelle (capture Playwright sur 5174 ou dans
le worktree) : le résultat doit se lire comme une coiffure à la taille où le
Bureau l'affiche.

## Critères d'acceptation

- [ ] Dans `design/bureau/Tete.tsx`, pour `court` et `chignon`, un rect de cheveux est dessiné de chaque côté du visage, sur la ligne `y` (première ligne du visage) ; un test de `Personnage.test.tsx` le vérifie dans les deux poses.
- [ ] Pour `chignon`, le rect du chignon mesure au moins 4 de large et 2 de haut, et son bas touche le haut de la bande de cheveux ; un test le vérifie.
- [ ] Un test vérifie que `long` et `chauve` dessinent les mêmes rects qu'avant.
- [ ] Le diff ne modifie ni `PersonnageAssis.tsx` ni `PersonnageDebout.tsx`.

## Dépendances

Aucune.

## Estimation

Un quart de journée.

## Risques

Le visage fait 6 unités : les tempes doivent rester hors des yeux (colonnes
`x + 1` et `x + 4`).