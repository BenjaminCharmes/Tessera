---
id: ticket-192
title: "Une notification système quand un run a besoin de vous, ou finit"
type: feat
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-26
---

# ticket-192 — Une notification système quand un run a besoin de vous, ou finit

## Objectif

Qu'on puisse lancer une file et passer à autre chose, en étant prévenu
quand un agent pose une question, quand un run se bloque, et quand une
file se termine.

## Contexte

Un run dure plusieurs minutes, une file plusieurs dizaines. Le seul signal
aujourd'hui est un toast dans la page, et seulement pour le projet regardé
(`App.tsx:99-118`). Une question d'agent expire au bout de
`dialogue_timeout_s` (ADR-025) : si personne ne regarde l'onglet, l'agent
repart sur une hypothèse alors qu'un humain était disponible, juste
ailleurs. Le ticket-186 a rendu la question visible dans l'UI ; ce ticket la
fait sortir de l'UI.

Les événements existent déjà sur le canal d'ADR-041 (`useSupervision.ts`) :
question posée, run bloqué, run fermé, file terminée.

## Solution proposée

- Un hook `useNotificationsSysteme` abonné aux événements de supervision,
  tous projets confondus, qui émet une notification pour : une question
  d'agent (avec le délai restant), un run `blocked`, la fin d'une file ou
  d'un run autonome, et un `provider_fallback` s'il existe (ticket-188).
  Pas de notification pour chaque ticket approuvé d'une file : le bruit
  tuerait le signal.
- Dans le navigateur : l'API `Notification` du web, permission demandée au
  premier run lancé, jamais au chargement.
- Dans l'app Tauri : le plugin `notification` de Tauri v2, avec la seule
  permission `notification:default`. Rien d'autre n'entre dans les
  capabilities : ADR-040 tient.
- Un clic sur la notification ramène la fenêtre au premier plan et
  sélectionne le projet concerné.
- Un réglage dans le panneau projets coupe les notifications ; il est
  mémorisé dans `localStorage` (même mécanisme que ticket-193).
- Aucune notification quand la fenêtre est au premier plan et que le projet
  concerné est celui affiché : le toast suffit.

## Critères d'acceptation

- [ ] Un test vérifie qu'un événement de question émet une notification dont
      le titre nomme le projet et le ticket
- [ ] Un test vérifie qu'un événement `agent_done` ordinaire n'en émet pas
- [ ] Un test vérifie qu'aucune notification ne part quand la fenêtre est
      visible et le projet affiché
- [ ] Un test vérifie que le réglage « couper » est respecté et survit à un
      rechargement
- [ ] `capabilities/default.json` de Tauri ne contient que
      `notification:default` en plus de l'existant
- [ ] `npm run test`, `npm run build` et `cargo check` passent

## Ce que ça ne fait pas

Pas de notification par e-mail ni sur mobile. Pas de son.

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

La permission web refusée une fois n'est plus redemandée par le navigateur :
le réglage doit dire clairement qu'elle est bloquée, pas seulement coupée.
