---
id: ticket-793
title: "The retest after rebase is timed per step and runs only the backend tests the rebase can affect"
type: feat
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
plan: true
estimated_days: 2
created: 2026-11-04
---

# ticket-793 — Le retest après rebase est chronométré par étape et ne lance que les tests backend que le rebase peut toucher

## Objectif

La livraison d'un ticket backend ne passe plus 12 à 17 minutes à relancer toute la suite après
le rebase, sans perdre ce que ce retest protège.

## Contexte

Mesuré le 04/11 sur la file ide-core (étape « tests relancés après rebase » de
`livraison_done`) : 13,2 min (752), 12,3 (754), 12,1 (751), 14,3 (760), 17,0 (766) ; 3 min pour
les tickets frontend (763, 764, 765). Un ticket dure 30 à 35 minutes : ce retest en est près de
la moitié.

`retest_apres_rebase.py` (ticket-568) relance la commande du testeur quand le rebase ramène des
commits de la base ; le ticket-584 l'évite quand base et branche ne touchent pas la même chaîne.
Dans une file, chaque ticket backend vient d'être mergé : le suivant partage toujours la chaîne
backend et relance tout `scripts/verifier.py` (pytest avec xdist, mypy natif et mypy-linux). La
CI de la PR rejoue de toute façon la suite complète avant le merge (`merge` exige une CI verte).

On ne sait pas aujourd'hui quelle étape coûte : `verifier.py` n'imprime pas de durée.

## Solution proposée

1. **Mesurer** : `scripts/verifier.py` imprime la durée de chaque étape (pytest, mypy,
   mypy-linux, tsc, eslint, vitest) sur une ligne finale ; l'étape de journal du retest la
   reprend.
2. **Cibler le retest** : `verifier.py` accepte une option (par ex. `--impact <ref>`) qui limite
   pytest aux fichiers de test concernés par les chemins modifiés entre `<ref>` et `HEAD` dans
   les deux sens : les tests modifiés eux-mêmes, et les tests qui importent un module
   `tessera.…` modifié (recherche du nom de module dans `backend/tests/`). mypy reste entier
   (incrémental, avec cache). Sans test concerné, pytest est sauté et le dit.
3. `retest_apres_rebase.py` passe cette option avec la base d'avant le rebase. La commande du
   testeur pendant le run, elle, ne change pas.
4. Échec fermé (ADR-039) : si les chemins modifiés ne se lisent pas, la suite complète tourne.

## Critères d'acceptation

- [ ] Un test vérifie que `verifier.py` imprime une ligne finale avec la durée de chaque étape
      lancée
- [ ] Un test vérifie que, avec l'option d'impact, la liste des fichiers pytest contient un test
      modifié et un test qui importe un module modifié, et exclut un test sans rapport
- [ ] Un test vérifie que, si les chemins modifiés ne se lisent pas, pytest tourne sur toute la
      suite
- [ ] Un test de `retest_apres_rebase.py` vérifie, avec des doubles, que le retest lance la
      commande avec l'option d'impact et la base d'avant le rebase

## Ce que ça ne fait pas

La CI reste la porte complète : elle rejoue toute la suite sur la PR. Le testeur du run lance
toujours la suite selon `pipeline.test_command`.
