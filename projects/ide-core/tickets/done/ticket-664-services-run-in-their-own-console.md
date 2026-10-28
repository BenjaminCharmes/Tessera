---
id: ticket-664
title: "A service runs in its own console, so its Ctrl+C no longer stops the backend"
type: fix
status: done
pr_number: null
priority: critical
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-10-28
---

# ticket-664 — Un service tourne dans sa propre console

## Objectif
Qu'un service lancé par Tessera ne puisse plus arrêter le backend qui l'a lancé.

## Contexte
Le 28/10, le backend 8100 s'est arrêté trois fois, en emportant tous ses enfants.
Chaque fois, c'était quelques minutes après un démarrage des services de Curio,
dont le backend venait de passer en `uvicorn --reload` (PR curio #36). Sous
Windows, un rechargement d'uvicorn envoie `CTRL_C_EVENT` à son processus de
travail, et Windows remet cet événement à **tous** les processus de la console.
Lancé par Tessera, le service partageait la console du backend : celui-ci
recevait le Ctrl+C, fermait son port (le premier arrêt, « figé sans port »),
puis s'arrêtait.

Reproduit dans un processus créé par WMI, comme le backend : sans le correctif,
le Ctrl+C d'un enfant atteint le parent ; avec, le parent survit.

## Solution proposée
`options_de_lancement` (`services/lancement.py`) donne à un service, sous
Windows, sa propre console sans fenêtre et son propre groupe de processus
(`CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP`) ; ailleurs, sa propre session,
comme avant. `ProcessRegistry._lancer` l'utilise.

## Critères d'acceptation
- [x] Un test vérifie que, sous Windows, `options_de_lancement` pose `CREATE_NO_WINDOW` et `CREATE_NEW_PROCESS_GROUP`, et ailleurs `start_new_session`
- [x] Reproduction réelle : un enfant lancé avec ces options envoie `CTRL_C_EVENT` à sa console, et le parent survit

## Ce que ça ne fait pas
- Ne change pas le lancement des agents (Agent SDK) ni du testeur. Un serveur
  avec `--reload` lancé par un agent dans sa propre commande pourrait encore
  toucher la console du backend : c'est à examiner dans l'audit de sécurité (ticket-654).
