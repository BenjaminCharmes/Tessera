---
id: ticket-128
title: "Lancer un run par POST et l'observer sur un canal partagé"
type: refactor
status: in-review
pr_number: null
priority: high
agent: codeur
depends_on: ["ticket-127"]
estimated_days: 2
created: 2026-09-23
---

# ticket-128 — Lancer un run par POST et l'observer sur un canal partagé

## Objectif

Découpler un run de la socket qui l'a lancé : il démarre par un POST, et
n'importe quel client l'observe — tous projets confondus — sur un canal unique.

## Contexte

Aujourd'hui `WS /orchestrator/stream/{project_id}` **déclenche** le run : le
client envoie le payload de démarrage à l'ouverture. Trois conséquences :
fermer l'onglet rend aveugle jusqu'à la fin du run ; aucune vue ne montre ce
qui tourne ailleurs ; répondre à un agent qui pose une question (ADR-025)
n'est possible que depuis cet onglet.

Par ailleurs seul le mode `single` passe un `run_id` à l'émetteur — `_stream_file`
et `run_autonomous` passent `run_id=None`, donc une file et un run autonome
n'ont **aucun historique en base**.

## Solution proposée

**Démarrage** — `POST /api/v1/orchestrator/run` couvre les trois modes,
démarre une tâche `asyncio`, renvoie `{"run_id": ...}` sans attendre la fin.
Le verrou projet est acquis **dans la tâche** ; un projet occupé répond 409.

**Suppression** — `WS /orchestrator/stream/{project_id}` disparaît. Deux
façons de lancer un run divergeraient (ADR-034).

**Observation** — `WS /api/v1/orchestrator/observe`, sans projet dans l'URL,
authentifié comme les autres routes WebSocket (ticket-120) :

- à la connexion, un instantané du registre ;
- ensuite, les **transitions** de tous les runs ;
- `{"subscribe": "<run_id>"}` ajoute `agent_token` et `agent_tool_use` de ce
  run ; `unsubscribe` les retire ;
- `{"type": "answer" | "interject" | "stop", "run_id", "text"}` est routé vers
  le `DialogueChannel` que le registre détient pour ce run.

Chaque message porte son `run_id` et son `project_id`.

**Persistance** — les trois modes ouvrent une ligne de run et la ferment,
plus seulement `single`.

Le frontend est adapté au minimum pour rester fonctionnel ; la vue de
supervision est le sujet de ticket-129.

## Critères d'acceptation

- [ ] `POST /api/v1/orchestrator/run` renvoie un `run_id` en moins d'une
      seconde pour un pipeline simulé qui dure plus longtemps
- [ ] `POST /api/v1/orchestrator/run` répond 409 sur un projet déjà occupé, en
      nommant le ticket en cours
- [ ] La route `WS /orchestrator/stream/{project_id}` n'existe plus dans
      `routers/orchestrator.py`
- [ ] Un test vérifie qu'un run se poursuit jusqu'à son commit après
      déconnexion de tous les observateurs
- [ ] Un test vérifie qu'un observateur reçoit l'instantané des runs déjà
      actifs à la connexion
- [ ] Un test vérifie qu'un observateur non abonné ne reçoit aucun
      `agent_token`, et en reçoit après `subscribe`
- [ ] Un test vérifie qu'un `answer` atteint le bon `DialogueChannel` quand
      deux runs tournent sur deux projets
- [ ] Un test vérifie qu'un run de file et un run autonome ouvrent et ferment
      une ligne en base
- [ ] `WS /observe` refuse la connexion sans jeton quand `STATIC_TOKEN` est
      renseignée
- [ ] `npm run build` et `npm run test` passent côté frontend
- [ ] `uv run pytest` passe ; `uv run mypy src/` passe sans erreur

## Dépendances

ticket-127.

## Estimation

2 jours.

## Risques

Touche le cœur du pipeline. Deux pièges connus, tous deux déjà payés par
ticket-079 et ticket-121 : un émetteur qui lève sur socket morte interrompt le
run avant son commit, et un `finish_run` placé après une écriture réseau
disparaît quand la socket meurt. Les propriétés de `emetteur()` doivent
survivre au refactor.

ADR-025 change de transport, pas de sémantique : délai, reprise sur hypothèse
énoncée et file distincte des interjections restent inchangés. Un ADR
accompagne le ticket.
