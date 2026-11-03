---
id: ticket-743
title: "An observer closed by its browser is logged as info, not as a warning"
type: fix
status: todo
pr_number: null
priority: low
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-11-03
---

# ticket-743 — Un observateur fermé par son navigateur se journalise en info

## Objectif

Le journal de Tessera ne montre plus d'avertissement quand un onglet qui observait un
run se ferme.

## Contexte

03/11 : la salle Tessera affiche en jaune des rafales de `observateur_interrompu`
(quatre à la même seconde à la fermeture de navigateurs de capture). Dans
`backend/src/tessera/routers/observation.py`, seul `WebSocketDisconnect` est traité
comme une fin normale ; un envoi sur une socket déjà fermée lève une autre exception
(`RuntimeError` de Starlette, `ConnectionClosed`…) et tombe dans
`except Exception` → `warning`. Le run n'est pas touché, mais l'avertissement noie les
vrais.

## Solution proposée

- Reconnaître les exceptions d'envoi sur une socket fermée comme une fin normale :
  journal en `info` (`observateur_ferme`).
- Toute autre exception reste un `warning` `observateur_interrompu`, qui nomme le type
  de l'exception.

## Critères d'acceptation

- [ ] Un test vérifie qu'un envoi qui lève l'erreur d'une socket fermée journalise
      `observateur_ferme` en `INFO` et aucun `WARNING`
- [ ] Un test vérifie qu'une autre exception journalise `observateur_interrompu` en
      `WARNING` avec le nom du type d'exception
- [ ] Un test vérifie que l'abonnement est fermé dans les deux cas

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

Aucun : la boucle ne change pas, seul le niveau de journal change.
