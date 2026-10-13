---
id: ticket-416
title: "One endpoint lists every project app running locally, launched by Tessera or by hand, with its ports and memory"
type: feat
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-10-13
plan: true
---

# ticket-416 — Inventaire des apps de projet qui tournent en local

## Objectif

Savoir, en un appel, quelles apps de projet tournent sur la machine, combien
de mémoire elles prennent, et pouvoir arrêter celles qu'on a oubliées.

## Contexte

Demande de Benjamin le 2026-10-13 : « parfois j'ai des projets qui tournent
et que j'oublie, et j'ai l'impression que ça bouffe de la mémoire ».

Aujourd'hui, `PROCESS_REGISTRY` (`services/process_registry.py`) ne connaît
que les services lancés **par** Tessera, en mémoire du backend, sans mesure
de mémoire. Une app lancée à la main (le 13/10 : vigie sur 8025/5195,
démarrée hors Tessera) est invisible, alors que ses ports sont déclarés dans
`agents.json` (`services[].commande`, `--port N`) ou dans
`frontend/vite.config.ts` (`server.port`).

## Solution proposée

- `GET /api/v1/services/running` : une entrée par app détectée :
  `{ project_id, project_name, nom, origine: "tessera" | "externe", pid,
  ports: [int], demarre_a, memoire_mo }`.
  - `tessera` : les services vivants du registre ; mémoire = RSS du
    processus **et de ses descendants**.
  - `externe` : pour chaque port déclaré par un projet (commande de service,
    `vite.config.ts`), un processus qui l'écoute sur la machine et qui n'est
    pas déjà compté côté `tessera` ; même mesure de mémoire.
  - Le backend de Tessera lui-même (8100) et son frontend (5173) sont exclus.
- `POST /api/v1/services/running/{pid}/stop` : arrête l'arbre de processus,
  **seulement** si ce pid figure dans l'inventaire courant (jamais un pid
  arbitraire) ; 404 sinon. Un service `tessera` passe par
  `PROCESS_REGISTRY.arreter`.
- Mesure et détection : `psutil` est l'outil évident, mais Smart App Control
  bloque certaines DLL sur la machine de dev (mypy, rpds-py) : le tour de
  plan vérifie que `psutil` s'importe ; sinon, repli sans dépendance
  (`netstat -ano` + `tasklist` sous Windows, `ss`/`ps` ailleurs), derrière
  une interface unique testable avec un faux.

## Critères d'acceptation

- [ ] Un test vérifie qu'un service vivant du registre apparaît avec
      `origine: "tessera"`, son pid et une mémoire numérique
- [ ] Un test (sonde système simulée) vérifie qu'un processus écoutant un
      port déclaré par un projet apparaît avec `origine: "externe"` et le
      bon `project_id`
- [ ] Un test vérifie qu'un même processus n'apparaît pas deux fois
- [ ] Un test vérifie que les ports 8100 et 5173 de Tessera sont exclus
- [ ] Un test vérifie que `POST …/{pid}/stop` renvoie 404 pour un pid absent
      de l'inventaire et n'arrête rien
- [ ] Un test vérifie l'extraction des ports depuis `--port 8026` dans une
      commande et depuis `port: 5196` dans un `vite.config.ts`

## Dépendances

Aucune. Le ticket-417 (la vue) en dépend.

## Ce que ça ne fait pas

- Pas d'apps « en ligne » (déploiements distants) : plus tard.
- Pas d'historique de consommation.
