---
id: ticket-557
title: "Project card actions sit on one aligned row, and the queue button adds to a running queue"
type: fix
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 0.25
created: 2026-10-23
---

# ticket-557 — Les actions d'une carte de projet sur une seule rangée

## Objectif
Que le pied d'une carte de projet soit propre quelle que soit la
combinaison de boutons, et que « File » serve aussi quand une file tourne.

## Contexte
Le 23/10, Benjamin a relevé des cartes décalées. Les trois boutons venaient
de trois composants aux styles différents : « Mettre en ligne » sur le
`Button` de la charte, « Lancer » en classes à la main (`text-xs`), « File »
en `text-micro`, sur sa propre rangée à gauche ; les compteurs se
repliaient entre les boutons. « File » était aussi grisé dès qu'un run
tournait, avec la raison seulement au survol, alors que l'API sait ajouter
des tickets à une file ouverte (ticket-478).

Fait à la main (retouche d'interface).

## Solution
- Pied de carte : dates, compteurs, puis une seule rangée d'actions alignée
  à droite et repliable : File, Mettre en ligne, Lancer.
- `LancerFile` et `BoutonServices` passent sur le `Button` compact de la
  charte ; « Arrêter » prend la variante `arret`.
- Une file en cours sur le projet : le bouton devient « Ajouter à la file
  (n) » et appelle `POST /orchestrator/runs/{id}/append`. Un run d'un seul
  ticket : bouton grisé et « Run en cours » écrit à côté.

## Critères d'acceptation
- [x] Un test montre que File et Lancer sont dans la rangée `actions-de-carte`, sans les compteurs
- [x] Un test montre que File et Lancer ont la même hauteur compacte (`h-[26px]`)
- [x] Un test montre l'ajout à la file en cours, avec le bilan « 1 ajouté »
- [x] Un test montre « Run en cours » écrit à côté du bouton grisé
- [x] Un test montre le message d'une file qui n'accepte plus de tickets (409)
- [x] Capture Playwright de la vue Projets relue (cartes Kadoomi, Devinoo, ide-core)
