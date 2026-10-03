---
agent: codeur
created: 2026-10-02
depends_on: []
estimated_days: 0.5
id: ticket-330
pr_number: null
priority: medium
status: done
title: The backend writes its logs to a rotating file, so a crash leaves a trace
type: chore
---

# ticket-330 — Le backend écrit ses journaux dans un fichier

## Objectif

Qu'un arrêt du backend laisse une trace qu'on puisse lire après coup.

## Contexte

Le 2026-10-02, le backend est tombé deux fois sans laisser de trace : vers
20:42 UTC (tous les agents en cours tués, code 129), puis plus tôt dans la
soirée. Il écrivait sur sa sortie standard, et rien ne la recueillait : il a
été impossible de savoir pourquoi. Une session l'a ensuite relancé à la main
en redirigeant sa sortie vers `backend/logs/backend.{out,err}.log`.

## Solution proposée

- Au démarrage, le logger structuré ajoute un gestionnaire de fichier
  tournant (`backend/logs/tessera.log`, par exemple 5 fichiers de 10 Mo),
  en plus de la sortie standard. Le dossier est créé s'il manque, et ignoré
  par git (`*.log` l'est déjà).
- Les exceptions non rattrapées d'une tâche de fond (`asyncio`) y sont
  journalisées avec leur trace.

## Critères d'acceptation

- [ ] Un test vérifie qu'après la configuration du logger, un message
      journalisé apparaît dans le fichier configuré
- [ ] Un test vérifie que le dossier du fichier est créé s'il n'existe pas
- [ ] Un test vérifie qu'une exception non rattrapée dans une tâche `asyncio`
      est écrite dans le fichier avec sa trace
- [ ] `.gitignore` couvre le fichier de journal

## Dépendances

Aucune.