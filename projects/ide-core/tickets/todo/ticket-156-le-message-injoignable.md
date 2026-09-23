---
id: ticket-156
title: "Le message « ajoute une liste services » ne s'affiche jamais"
type: fix
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: ["ticket-155"]
estimated_days: 1
created: 2026-09-23
---

# ticket-156 — Dire quoi écrire à un projet qui ne déclare rien

## Objectif

Qu'un projet sans `services` puisse apprendre qu'il pourrait en déclarer,
sans pour autant se voir proposer un lancement qui n'existe pas.

## Contexte

`PanneauServices` porte un composant `RienDeclare` qui explique quoi écrire
dans `agents.json`, et sa docstring affirme : « Quand rien n'est déclaré, ce
panneau ne disparaît pas — il dit quoi écrire. Masquer la fonctionnalité
répondait au symptôme sans répondre au besoin. »

C'est faux. Le seul endroit qui met `servicesOuverts` à vrai est
`onOuvrirLePanneau`, appelé par `BoutonServices` — qui commence par
`if (!services.declare) return null;`. Aucun bouton, donc aucun clic, donc le
panneau ne s'ouvre jamais, et `RienDeclare` n'a jamais été affiché à personne.

Le ticket-155 n'y change rien : il ouvre le panneau quand un service tourne
ou vient de mourir, ce qui suppose un service déclaré.

Le cas est réel — `carriere` et `vega` rendent tous deux `[]` sur
`GET /services`. Certains projets n'ont pas vocation à être lancés (des
scripts), et pour eux le silence actuel convient. Ce qui manque, c'est le
choix : rien ne distingue « ce projet ne se lance pas » de « personne n'a
encore écrit la commande ».

## Contrainte

ADR-042 pose que ne rien déclarer **est** la réponse « ce projet ne se lance
pas depuis l'IDE », et qu'il n'y a donc pas de bouton. La solution ne doit
pas rouvrir un bouton de lancement : elle doit rendre une explication
accessible sans en promettre l'action.

## Solution proposée

Une piste, à trancher : une affordance neutre dans l'en-tête — pas un
lancement — qui déplie la même explication. À défaut, retirer `RienDeclare`
et sa docstring plutôt que de garder du code que rien n'atteint.

## Critères d'acceptation

- [ ] Un test rend le chemin choisi et vérifie que l'explication est
      atteignable sur un projet qui déclare `[]`
- [ ] Aucun bouton de lancement n'apparaît sur un projet sans `services`
- [ ] Si la décision est de supprimer `RienDeclare`, plus aucune docstring
      ne prétend qu'il s'affiche

## Dépendances

ticket-155.

## Estimation

1 jour.

## Risques

Une affordance de plus dans un en-tête déjà chargé — « VSCode », « Git »,
« Lancer ». Le coût d'une ligne inutile se paie sur chaque projet.
