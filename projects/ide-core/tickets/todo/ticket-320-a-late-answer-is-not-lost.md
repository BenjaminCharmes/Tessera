---
id: ticket-320
title: "An answer sent after its question expired is not lost: it is delivered as a message and the screen says so"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-02
---

# ticket-320 — Une réponse arrivée trop tard n'est pas perdue

## Objectif

Que l'utilisateur sache si sa réponse à un agent est arrivée, et qu'une
réponse tardive serve quand même.

## Contexte

Le 2026-10-02, le codeur du ticket-316 a posé une question à 13:09:58, avec
une expiration à 13:14:58 (ADR-025). L'utilisateur a répondu sans savoir si
sa réponse était passée. Aucune trace dans la base : `DialogueChannel.answer`
(`services/dialogue.py:119-124`) ignore une réponse quand plus aucune
question n'attend, et le note seulement dans le journal du backend
(`reponse_sans_question`). L'écran, lui, ne dit rien.

## Solution proposée

- Une réponse sans question en attente est déposée comme message spontané
  (`interject`) : l'agent la lira au tour suivant (ADR-025, corollaire).
- Le backend émet un événement qui dit ce qu'il a fait de la réponse :
  transmise à la question, ou déposée pour le tour suivant.
- La vue du run affiche cet accusé sous le champ de réponse.
- Une question expirée s'affiche comme telle (« expirée à 13:14, l'agent a
  repris sur une hypothèse »), avec l'hypothèse quand l'agent l'a énoncée.

## Critères d'acceptation

- [ ] Un test vérifie qu'`answer()` sans question en attente dépose le texte
      dans la boîte aux lettres, que `drain()` rend ensuite
- [ ] Un test vérifie qu'une réponse émet un événement qui distingue
      « transmise » de « déposée pour le tour suivant »
- [ ] Un test du frontend vérifie que l'accusé « déposée pour le tour
      suivant » s'affiche après une réponse tardive
- [ ] Un test du frontend vérifie qu'une question expirée s'affiche comme
      expirée, et non plus comme en attente

## Dépendances

Aucune.
