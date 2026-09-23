---
id: ticket-155
title: "Les services restent visibles après un rechargement, et se lisent proprement en supervision"
type: fix
status: in-review
pr_number: null
priority: high
agent: codeur
depends_on: ["ticket-154"]
estimated_days: 1
created: 2026-09-23
---

# ticket-155 — Des services visibles sans re-cliquer, et lisibles en supervision

## Objectif

Qu'un projet dont les services tournent montre son panneau sans qu'on ait à
relancer quoi que ce soit, et que la supervision distingue chaque service de
sa sortie à l'œil.

## Contexte

Après `Ctrl+R`, le bouton affiche bien « Arrêter » en bleu — l'état vient du
backend — mais le panneau en dessous a disparu. `servicesOuverts` est un
`useState(false)` dans `Sidebar`, et rien ne l'ouvre sauf un clic sur le
bouton. Or ce clic **lance ou arrête** : pour revoir l'adresse d'un service
déjà lancé, il fallait l'arrêter.

L'information existait pourtant : elle n'était accessible que depuis l'onglet
Supervision, ce qui est exactement le reproche auquel le ticket-147 répondait.

En supervision, le nom du service et ses deux adresses tiennent sur une seule
rangée de puces, sans séparation visible entre un lien et le suivant, et les
blocs de sortie dépliés sont rendus **après** toutes les puces — donc loin du
service auquel ils appartiennent.

## Solution proposée

`PanneauxDuProjet` décide de l'ouverture : le panneau s'affiche dès qu'un
service tourne, sans attendre un clic. Le clic reste ce qui l'ouvre quand
rien ne tourne encore.

`ServicesLances` passe d'une rangée de puces à une liste : un bloc par
service, son en-tête puis, replié dessous, sa sortie. Chaque adresse devient
une pastille bordée portant son étiquette, donc lisible séparément.

## Critères d'acceptation

- [ ] `PanneauxDuProjet` rend le panneau quand `services.enCours` est vrai
      et que `servicesOuverts` est faux
- [ ] Il ne le rend pas quand rien ne tourne et qu'aucun clic n'a eu lieu
- [ ] En supervision, la sortie dépliée d'un service est rendue dans le même
      bloc que son nom
- [ ] Chaque adresse est un lien distinct portant son étiquette
- [ ] `npm run typecheck`, `npm run lint` et `npm run test -- --run` passent

## Dépendances

ticket-154 (les adresses).

## Estimation

0,5 jour.

## Risques

Ouvrir d'office prend de la place dans une barre latérale étroite ; le
panneau reste borné en hauteur et défilable, comme avant.
