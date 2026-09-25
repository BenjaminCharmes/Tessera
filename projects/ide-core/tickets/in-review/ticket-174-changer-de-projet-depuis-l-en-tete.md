---
id: ticket-174
title: "Changer de projet oblige à repasser par l'onglet Projets"
type: feat
status: in-review
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-25
---

# ticket-174 — Changer de projet depuis l'en-tête

## Objectif

Qu'on passe d'un projet à l'autre sans quitter ce qu'on regarde.

## Contexte

Le nom du projet actif s'affiche en haut de la barre latérale, à côté de
« Lancer », « VSCode » et « Git ». Pour en changer, il faut ouvrir l'onglet
« Projets », cliquer, puis revenir à l'onglet d'où l'on venait — Tickets,
Supervision, Coûts.

Sur un seul projet, c'est sans importance. À neuf projets, et avec des runs en
parallèle sur plusieurs d'entre eux (ADR-038), c'est le geste le plus fréquent
de la session, et le plus coûteux : il fait perdre la vue courante.

## Solution proposée

Le nom du projet devient un déclencheur : il ouvre la liste des projets, on en
choisit un, la vue courante ne bouge pas.

## Critères d'acceptation

- [ ] Le nom du projet ouvre une liste des projets disponibles
- [ ] Choisir un projet change le projet actif **sans** changer d'onglet
- [ ] La liste se ferme au choix, au clic en dehors et à `Échap`
- [ ] Le projet actif est identifié dans la liste
- [ ] L'ensemble est atteignable au clavier
- [ ] `npx vitest run`, `tsc` et `eslint` passent

## Dépendances

Aucune. Se combine avec ticket-175 si les projets sont groupés.

## Estimation

1 jour.

## Risques

Un en-tête déjà chargé — « Lancer », « VSCode », « Git ». Le déclencheur est le
nom lui-même, pas un bouton de plus : la rangée n'y gagne aucun élément.
