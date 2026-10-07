---
agent: codeur
created: 2026-10-07
depends_on: []
estimated_days: 0.25
id: ticket-365
pr_number: null
priority: high
status: in-review
title: A card whose PR is merged or closed does not ask again when the window comes
  back
type: fix
---

# ticket-365 — Une PR réglée n'est pas redemandée au retour de la fenêtre

## Objectif

Revenir sur la fenêtre de Tessera ne doit pas relancer l'appel `pr-status`
des cartes dont la PR est déjà mergée ou fermée.

## Contexte

`frontend/src/components/Sidebar/TicketCard.tsx` interroge
`api.github.getPrStatus` au montage puis toutes les 30 s, et s'arrête quand
la PR est `merged` ou `closed`. Depuis le ticket-356, l'effet dépend de
`useFenetreVisible` : quand la fenêtre redevient visible, il se relance et
redemande l'état de **toutes** les cartes, y compris celles dont la PR est
réglée depuis longtemps. Sur ide-core, 139 cartes : chaque retour sur la
fenêtre relance 139 appels (mesuré le 2026-10-07).

## Solution proposée

Retenir dans la carte qu'une PR est réglée (`merged` ou `closed`, déjà connu
par `prStatus`) et ne relancer ni l'appel ni l'intervalle dans ce cas, même
quand la fenêtre redevient visible. Une PR ouverte garde le comportement
actuel : pause fenêtre cachée, reprise au retour.

## Critères d'acceptation

- [ ] Un test de `frontend/src/components/Sidebar/TicketCard.test.tsx` rend une carte dont la PR est mergée, cache puis réaffiche la fenêtre, et vérifie que `getPrStatus` n'a été appelé qu'une fois
- [ ] Un test de `frontend/src/components/Sidebar/TicketCard.test.tsx` vérifie la même chose pour une PR fermée
- [ ] Un test de `frontend/src/components/Sidebar/TicketCard.test.tsx` vérifie qu'une PR ouverte est redemandée quand la fenêtre redevient visible
- [ ] Les tests existants de `frontend/src/components/Sidebar/TicketCard.test.tsx` passent sans modification

## Dépendances

Aucune.

## Estimation

0,25 jour.

## Risques

Aucun pour une PR ouverte, dont le comportement ne change pas.

## Ce que ça ne fait pas

- Ne met rien en cache côté backend (ticket-364).
- Ne regroupe pas les appels par projet.