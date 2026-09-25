---
id: ticket-173
title: "L'adresse d'un service se rend de deux façons différentes"
type: refactor
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-25
---

# ticket-173 — Une adresse de service, deux rendus

## Objectif

Qu'une adresse de service se présente de la même façon partout.

## Contexte

Le même lien vers `http://localhost:5174/` s'affiche différemment selon
l'endroit :

- barre latérale — `PanneauServices` : texte souligné en pointillés, pleine
  largeur, sous le nom du service
- Supervision — `ServicesLances` : pastille bordée, en ligne, à côté du nom

Ce n'est pas une divergence de style à harmoniser : ce sont **deux
implémentations** du même affichage, écrites à deux moments. Les deux appellent
`adressesDansLaSortie`, puis chacune redessine le lien à sa façon. C'est la
dérive qu'ADR-034 vise, et ADR-026 la nomme aussi — les tailles et les
affordances se décident une fois.

La forme de la Supervision est la bonne : bordée, elle se lit comme ce qu'elle
est — quelque chose qu'on peut cliquer — là où un soulignement pointillé se lit
comme une note de bas de page.

## Solution proposée

Extraire un composant unique, utilisé aux deux endroits. Aucun des deux ne
redessine plus le lien.

## Critères d'acceptation

- [ ] Un seul composant rend l'adresse d'un service
- [ ] `PanneauServices` et `ServicesLances` l'utilisent tous les deux
- [ ] Le rendu est celui de la Supervision — bordé, en ligne
- [ ] L'étiquette (`Local`, `Network`…) reste lisible quand elle existe
- [ ] `npx vitest run`, `tsc` et `eslint` passent

## Dépendances

Aucune.

## Estimation

Moins d'une journée.

## Risques

La barre latérale est plus étroite que la Supervision : une pastille y tient
moins bien qu'un lien pleine largeur. À vérifier à 320 px avant de conclure.
