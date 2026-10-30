---
id: ticket-718
title: "A red retest after rebase runs once more before stopping the delivery"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-30
---

# ticket-718 — Un retest rouge après rebase est relancé une fois avant d'arrêter la livraison

## Objectif
Un test instable ne doit plus suffire, à lui seul, à arrêter la livraison d'un
ticket approuvé, ni toute la file derrière lui.

## Contexte
Le 30/10, deux livraisons approuvées par toutes les étapes se sont arrêtées sur
un test rouge après rebase, puis vert à chaque relance à la main : ticket-703
(`test_provider_agent_sdk.py`, corrigé par le ticket-716) et ticket-706
(`test_delai_detaille.py`, corrigé par le ticket-717). Chaque fois, la file
entière s'est arrêtée (« file interrompue »). Côté Curio, le ticket-052 a subi la
même chose le 29/10. `RetestApresRebase.juger`
(`backend/src/tessera/services/retest_apres_rebase.py`) arrête la livraison dès
le premier essai rouge.

## Solution proposée
Dans `juger` : quand le premier essai est rouge, relancer une fois.
- Vert au second essai : la livraison continue. L'étape du journal le dit
  (« vert au 2e essai ») et reprend le début de la sortie du premier échec, pour
  que l'instabilité reste visible et devienne un ticket.
- Rouge deux fois : l'arrêt est celui d'aujourd'hui.
- Un premier essai qui expire ou ne démarre pas compte comme rouge. Il est
  relancé de la même façon.

## Critères d'acceptation
- [ ] `test_red_then_green_retest_continues_and_says_so` (dans `backend/tests/test_retest_apres_rebase.py`) : un lanceur rouge puis vert donne un `Jugement` sans `arret`, dont l'étape contient « 2e essai » et le début de la première sortie
- [ ] `test_red_twice_retest_stops` : un lanceur rouge deux fois donne un `arret`, et le lanceur est appelé exactement deux fois
- [ ] `test_green_first_retest_runs_once` : un lanceur vert d'emblée est appelé une seule fois
- [ ] `test_no_test_command_still_records_nothing` : `TestCommandNotFound` rend toujours `None`, sans second appel

## Ce que ça ne fait pas
- Ne relance pas les tests du testeur pendant le run : seul le retest de livraison est concerné
- Ne masque pas l'instabilité : elle reste écrite dans le journal
