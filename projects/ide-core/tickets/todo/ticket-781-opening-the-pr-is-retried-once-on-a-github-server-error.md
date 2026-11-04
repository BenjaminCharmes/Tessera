---
id: ticket-781
title: "Opening the PR is retried once on a GitHub server error"
type: fix
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-11-04
---

# ticket-781 — L'ouverture de la PR est retentée une fois sur une erreur serveur de GitHub

## Objectif

Une livraison approuvée ne s'arrête plus parce que GitHub a répondu une seule fois par une
erreur 5xx en ouvrant la PR.

## Contexte

04/11, ticket-749 : `Livraison interrompue : HTTPStatusError: Server error '500 Internal Server
Error' for url '.../pulls'`. La branche était poussée ; la PR a été ouverte à la main (#870).
Le même matin, GitHub a renvoyé d'autres 500 passagers (suppression de branche, push).

`_ouvrir_la_pr` (`backend/src/tessera/services/livraison.py`) traite déjà
`httpx.TransportError` : il cherche une PR ouverte malgré la réponse perdue (ticket-455). Une
`httpx.HTTPStatusError` de statut 5xx remonte telle quelle. Le ticket-739 ne couvre que la
phase 2 (CIWatcher).

## Solution proposée

- Sur une `HTTPStatusError` de statut ≥ 500, chercher d'abord une PR ouverte malgré l'erreur
  (même recherche que ticket-455) ; à défaut, attendre un court délai puis retenter
  `open_pull_request` **une** fois.
- Une seconde erreur, ou un statut 4xx, garde le comportement actuel : l'arrêt est rendu.
- L'étape journalisée dit qu'une nouvelle tentative a eu lieu.

## Critères d'acceptation

- [ ] Un test vérifie, avec des doubles, qu'une erreur 500 puis un succès ouvrent la PR et
      journalisent « nouvelle tentative »
- [ ] Un test vérifie que deux erreurs 500 de suite rendent l'arrêt, avec deux appels seulement
- [ ] Un test vérifie qu'une erreur 422 n'est pas retentée
- [ ] Un test vérifie qu'une erreur 500 alors que la PR existe déjà reprend cette PR sans en
      ouvrir une seconde
