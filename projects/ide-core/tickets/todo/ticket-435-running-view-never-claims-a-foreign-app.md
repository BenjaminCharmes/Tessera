---
id: ticket-435
title: "The Running view only attributes an app to a project when the process really belongs to it, never on a port alone"
type: fix
status: todo
pr_number: null
priority: critical
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-14
---

# ticket-435 — « En cours » n'attribue jamais à un projet une app qui n'est pas la sienne

## Objectif

Qu'aucun bouton « Arrêter » de la vue « En cours » ne puisse tuer une
application étrangère aux projets, parce qu'elle écoute sur un port qu'un
projet déclare.

## Contexte

Capture du 2026-10-14 : la vue « En cours » montrait, sous **ide-core**, un
« backend lancé à la main » sur `localhost:8000`, avec « Arrêter » et
« Arrêter le projet ». C'était une autre application de la machine, sans
rapport avec Tessera. `projects/ide-core/agents.json` déclarait encore le
port 8000 pour le backend de Tessera (passé au 8100 depuis ; corrigé à la
main) ; l'inventaire du ticket-416 (`services/inventaire_apps.py`,
`_apps_externes`) attribue au projet **tout** processus qui écoute un port
déclaré.

## Solution proposée

- Une app `externe` n'est attribuée à un projet que si son processus (ou
  son parent direct) a une ligne de commande ou un répertoire de travail
  situé sous le dossier du projet (chemins résolus, casse ignorée sous
  Windows).
- Un port déclaré occupé par un processus étranger n'est pas une app du
  projet : il apparaît, au mieux, comme un avertissement « port 8000
  déclaré par ide-core, occupé par un autre programme », **sans** bouton
  d'arrêt, et ne compte pas dans la mémoire du projet.
- Le projet qui fait tourner l'IDE (`fait_tourner_l_ide`) n'a jamais d'app
  externe dans l'inventaire.
- `POST /services/running/{pid}/stop` refuse (404) un pid signalé en
  avertissement.

## Critères d'acceptation

- [ ] Un test (sonde simulée) vérifie qu'un processus écoutant un port
      déclaré, mais dont la ligne de commande et le répertoire sont hors du
      projet, n'est pas une app du projet
- [ ] Un test vérifie qu'un processus dont la ligne de commande est sous le
      dossier du projet reste attribué
- [ ] Un test vérifie que ce port occupé par un étranger est rendu comme
      avertissement, sans pid arrêtable
- [ ] Un test vérifie que `POST …/running/{pid}/stop` renvoie 404 pour ce pid
- [ ] Un test vérifie que le projet qui fait tourner l'IDE n'a aucune app
      externe

## Dépendances

Aucune.
