---
id: ticket-069
title: "Arrêter un run, et relire ce qu'il a produit"
type: feat
status: done
pr_number: null
priority: high
agent: codeur
depends_on: [ticket-068]
estimated_days: 1
created: 2026-09-17
---

# ticket-069 — Arrêter un run, et relire ce qu'il a produit

## Pourquoi

Deux manques constatés au premier usage réel.

**On ne pouvait pas arrêter un run.** Une fois lancé, il allait jusqu'au bout —
jusqu'à 3 tours × 6 agents — en écrivant sur disque. Le jour où un agent part de
travers, on le regarde faire.

**On ne pouvait pas voir ce qu'il avait produit.** Le pipeline relit le diff git
réel depuis ADR-018, `GitWorkspaceService.current_diff()` existe et tourne à
chaque run, mais rien ne l'exposait. Le 2026-09-17, deux tickets se sont
affichés `done` sans avoir rien commité, et rien à l'écran ne permettait de le
voir.

## Décision

**L'arrêt passe par le canal de dialogue**, qui est déjà le chemin par lequel
l'utilisateur parle à un run en cours. Il est vérifié **entre** les étapes,
jamais au milieu de l'une : couper un agent en plein tour jetterait un travail
déjà payé et laisserait un diff que personne n'a relu. Le run commite ce qu'il a
produit — ADR-018 fait dépendre le ticket suivant d'un arbre propre — et le
ticket passe `blocked`, pas `todo`, sinon un run autonome le reprendrait au tour
suivant et l'arrêt serait sans effet.

**Le diff se lit sur la branche du ticket contre sa base**, pas sur l'arbre de
travail : un run se termine par un commit et laisse l'arbre propre.
`base...branche` compare à l'ancêtre commun, sans quoi tout ce qui a avancé sur
la base apparaîtrait comme retiré par le ticket.

L'écran distingue **trois états** qu'il serait faux de confondre : un ticket
jamais lancé, une branche qui existe mais ne contient rien, et un diff réel.
C'est précisément ce qui manquait pour voir la panne du 2026-09-17.

## Livré

- `DialogueChannel.request_stop()` — débloque aussi une question en attente,
  sinon arrêter un run suspendu n'aurait rien fait avant le délai d'ADR-025
- `finish_stopped` — commite, émet `stopped_by_user`, bloque le ticket
- Points de contrôle entre les étapes de `run_pipeline`
- `services/ticket_diff.py` + `GET /projects/{id}/tickets/{id}/diff`
- `components/DiffView` — Monaco en `language="diff"`, lecture seule
- Bouton d'arrêt dans le panneau, bouton « voir le diff » sur chaque ticket

## Vérifié

883 tests backend, mypy sur 64 fichiers, 326 tests frontend, 5 flows E2E,
`npm run build`.
