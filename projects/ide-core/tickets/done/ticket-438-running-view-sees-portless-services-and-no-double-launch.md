---
agent: codeur
created: 2026-10-14
depends_on: []
estimated_days: 1
id: ticket-438
plan: true
pr_number: 440
priority: high
status: done
title: The Running view also finds a project's declared services that listen on no
  port, and Launch refuses when the project already runs
type: fix
---

# ticket-438 — Les services sans port sont vus, et « Lancer » ne double rien

## Objectif

Qu'« Arrêter le projet » arrête vraiment tout le projet, et que « Lancer »
ne démarre pas une seconde copie d'une app qui tourne déjà.

## Contexte

Le 2026-10-14 sur vigie (services lancés à la main : API sur 8025, front sur
5195, `python -m app.worker` sans port) : après un « Arrêter le projet »
dans la vue « En cours », l'API et le front se sont arrêtés mais pas le
worker ; puis « Lancer » (`POST /api/v1/projects/vigie/services/start`) a
démarré les trois services déclarés, dont un **second worker** — deux
workers ont coexisté, l'un des deux bloqué par le verrou de l'autre.

Causes :
1. L'inventaire (`services/inventaire_apps.py`, tickets 416 et 435) ne
   trouve une app `externe` que par un port qu'elle écoute : un service
   déclaré sans port (`agents.json` → `services[].commande` sans `--port`
   ni serveur Vite) est invisible, donc ni affiché ni arrêté.
2. `POST …/services/start` (`routers/services.py`) ne regarde que le
   registre de Tessera, pas les processus du projet lancés hors de lui.

## Solution proposée

- Inventaire : pour chaque service déclaré, chercher aussi les processus
  dont la ligne de commande correspond à sa commande (module ou script
  reconnaissable, ex. `app.worker`) **et** qui appartiennent au projet
  (`attribution_processus`, ticket-435 : répertoire ou ligne de commande
  sous le dossier du projet). Ils apparaissent comme apps `externe` sans
  port, et « Arrêter le projet » les arrête avec les autres.
- `services/start` : si l'inventaire montre déjà une app du projet pour un
  service déclaré, ne pas le relancer — réponse 409 qui nomme le service et
  son pid, ou démarrage des seuls services absents (à trancher au tour de
  plan, en le disant dans la PR).
- La vue « En cours » montre ces apps sans port (« — » à la place du lien).

## Critères d'acceptation

- [ ] Un test (sonde simulée) vérifie qu'un processus `python -m app.worker`
      du projet, sans port, apparaît dans l'inventaire comme app `externe`
      du service `worker`
- [ ] Un test vérifie qu'un processus de même commande mais hors du dossier
      du projet n'est pas attribué : `python -m app.worker` existe dans
      vigie **et** dans affut (le 2026-10-14, la « veille » d'affût a été
      prise pour un worker de vigie) — l'appartenance se juge au dossier du
      projet (répertoire de travail ou exécutable de son `.venv`), jamais au
      nom du module
- [ ] Un test vérifie qu'« Arrêter le projet » (arrêt de toutes les apps du
      groupe) inclut le service sans port
- [ ] Un test vérifie que `services/start` ne lance pas un service déclaré
      dont une app tourne déjà, et dit lequel
- [ ] Un test frontend vérifie qu'une app sans port s'affiche avec « — » à la
      place du lien

## Dépendances

Aucune.