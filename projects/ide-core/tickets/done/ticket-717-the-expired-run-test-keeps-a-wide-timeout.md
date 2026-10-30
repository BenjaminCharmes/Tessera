---
id: ticket-717
title: "The expired-run test keeps a wide timeout"
type: test
status: done
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 0.1
created: 2026-10-30
---

# ticket-717 — Le test du run expiré garde un délai large

## Objectif
`test_an_expired_run_names_the_cut_step_and_its_time` ne doit plus échouer au
hasard sur une machine chargée.

## Contexte
Le 30/10 à 12:13, la livraison du ticket-706 (approuvé par toutes les étapes)
s'est arrêtée sur ce test, rouge après rebase et vert trois fois sur trois en
isolé. Avec un délai de 4 s, le démarrage de Python de l'étape rapide dépasse le
délai sous charge, et c'est elle qui est coupée, pas l'étape lente. Le test
voisin avait déjà été porté à 15 s pour la même raison.

## Fait
Délai de 15 s, comme le voisin ; les assertions ne changent pas d'intention.
Fait à la main. Le problème de fond (une livraison arrêtée par un seul test
instable) est le ticket-718.

## Critères d'acceptation
- [x] L'étape coupée reste l'étape lente (`time.sleep(60)`)
- [x] Le délai laisse à l'étape rapide une marge d'au moins 10 s
