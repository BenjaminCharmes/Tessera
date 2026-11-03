---
id: ticket-716
title: "The stream silence test keeps a wide timing margin"
type: test
status: done
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 0.1
created: 2026-10-30
---

# ticket-716 — Le test du silence de flux garde une marge de temps large

## Objectif
Que `test_run_aboutit_si_messages_plus_frequents_que_le_silence` ne puisse plus
échouer au hasard sur une machine chargée.

## Contexte
Le 30/10 à 08:54, la livraison du ticket-703, approuvé par toutes les étapes, s'est
arrêtée sur ce test, rouge après le rebase, puis vert cinq fois sur cinq en
isolé. Il espaçait les messages de 30 ms pour un seuil de 100 ms : sous xdist,
avec d'autres files en parallèle, un écart dépasse le seuil. C'est
vraisemblablement aussi le « tests rouges après rebase, non reproduits » du
ticket-052 de Curio.

## Fait
Écart de 250 ms pour un seuil d'1 s, cinq messages (1,25 s au total, toujours
au-dessus du seuil) : la marge passe de 3× à 4× et ne dépend plus de dizaines de
millisecondes. Fait à la main.

## Critères d'acceptation
- [x] Le test garde son intention : le total dépasse `silence_max_s`, chaque écart reste dessous
- [x] L'écart entre deux messages est au moins quatre fois plus petit que le seuil
