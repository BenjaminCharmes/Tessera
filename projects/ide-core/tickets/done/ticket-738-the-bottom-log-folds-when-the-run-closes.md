---
id: ticket-738
title: "The bottom log folds when the run closes"
type: fix
status: done
pr_number: null
priority: low
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-11-03
---

# ticket-738 — Le journal du bas se replie quand le run se ferme

## Objectif

Le journal du bas ne reste pas ouvert quand rien ne tourne.

## Contexte

Relevé au coup de pinceau (ticket-735, « Ce que ça ne fait pas ») : le journal
déplié pendant un run le reste après, et occupe 180 px de l'écran pour rien. Son
état est persisté (ticket-440), donc il reste ouvert aussi au rechargement.

## Solution proposée

`BottomPanel` replie le journal quand le dernier événement devient `run_closed`.
Pas `pipeline_done` : dans une file, il clôt chaque ticket, et le journal se
replierait entre deux tickets sous les yeux de qui le suit. Seule la transition
replie : un dépliage à la main au repos est respecté. Retouche faite à la main.

## Critères d'acceptation

- [x] `BottomPanel.test.tsx` vérifie que le journal se replie à `run_closed` et
      mémorise l'état replié
- [x] `BottomPanel.test.tsx` vérifie qu'il reste déplié après le `pipeline_done`
      d'un ticket de file, et tant que le run tourne
- [x] `BottomPanel.test.tsx` vérifie qu'on peut le redéplier à la main une fois le run fermé

## Ce que ça ne fait pas

Ne déplie pas le journal quand un run démarre : l'ouvrir reste un geste.
