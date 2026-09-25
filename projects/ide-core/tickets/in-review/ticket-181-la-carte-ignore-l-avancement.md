---
id: ticket-181
title: "La carte d'un run n'apprend jamais l'avancement d'une file"
type: fix
status: in-review
pr_number: null
priority: high
agent: codeur
depends_on: ["ticket-172", "ticket-179"]
estimated_days: 1
created: 2026-09-25
---

# ticket-181 — L'avancement arrive par un chemin que la carte ne lit pas

## Objectif

Qu'une file lancée sous les yeux de l'utilisateur affiche son avancement.

## Contexte

Cinq tickets lancés en file. La Supervision montre bien la carte, son ticket
courant, son étiquette « file » — mais **ni `1/5`, ni la liste dépliante**, que
ticket-172 et ticket-179 ont pourtant ajoutées.

Le backend, lui, envoie tout :

```json
{"ticket_id": "ticket-016", "mode": "queue", "file_index": 1, "file_total": 5,
 "file_restants": ["ticket-017", "ticket-018", "ticket-019", "ticket-020"]}
```

### La cause

Une carte se remplit par **deux** chemins, et un seul connaît ces champs.

L'**instantané**, à la connexion, porte le `RunActif` complet. Mais la
réservation du run précède son premier `queue_progress` : un onglet déjà
ouvert reçoit donc un instantané où `file_total` vaut encore 0, puis
l'avancement lui arrive en **événement**.

Or `majDesRuns` ne propage que quatre champs — agent, ticket, étape, tour — et
ignore les données de `queue_progress`. La carte garde `file_total: 0` jusqu'à
la fin du run.

C'est la troisième fois que le modèle du backend avance sans que la mise à jour
incrémentale du frontend suive : ticket-163 pour la question en attente,
ticket-172 pour l'avancement, celui-ci pour le chemin par événement. Les champs
ont été rendus optionnels pour réparer le build ; ça a masqué l'absence au lieu
de la signaler.

## Solution proposée

`majDesRuns` lit `queue_progress` comme le registre le fait : avancement,
restants, faits. Et un `queue_progress` sur un run inconnu le crée en `queue`,
pas en `single` — c'est ce que l'événement dit.

## Critères d'acceptation

- [ ] Un `queue_progress` met à jour l'avancement, les restants et les faits
- [ ] Un `queue_progress` sur un run inconnu le crée avec le mode `queue`
- [ ] Les autres événements ne touchent pas à ces champs
- [ ] Un run hors file n'acquiert jamais d'avancement
- [ ] `npx vitest run`, `tsc`, `eslint` et `npm run build` passent

## Dépendances

ticket-172 et ticket-179, dont il répare le chemin manquant.

## Estimation

Moins d'une journée.

## Risques

Aucun : ce sont des champs qu'aucun autre chemin n'écrit.
