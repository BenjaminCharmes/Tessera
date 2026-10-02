---
agent: codeur
created: 2026-10-02
depends_on: []
estimated_days: 1
id: ticket-321
pr_number: null
priority: high
status: done
title: 'The testeur shows in the run view: a Tests stage and a card that says why
  the codeur starts again'
type: feat
---

# ticket-321 — Le testeur apparaît dans la vue du run

## Objectif

Qu'on voie, dans la vue d'un run, que les tests ont tourné, ce qu'ils ont
rendu, et pourquoi le codeur repart sans passer par la revue.

## Contexte

Capture du 2026-10-02 (ticket-316) : la bande d'étapes ne montre que
Production et Revue, et la liste n'affiche que trois cartes CODEUR à la
suite. Pour l'utilisateur, « on ne voit plus que le codeur se renvoyer la
balle ».

Pourtant, le testeur a bien tourné entre deux : `testeur: 1 error in 2.32s`,
puis « tests rouges au tour 1 ». Mais :

- la bande d'étapes (`AgentPanel/StageStrip.tsx`) n'a pas d'étape Tests ;
- `test_result` n'a pas de carte dans le fil (`components/FilDuRun/`). Seul
  le Pipeline log en porte une ligne (ticket-279) ;
- une suite rouge renvoie au codeur sans revue (ticket-098), si bien que
  Sécurité, Revue et Validation n'apparaissent jamais pour ce tour.

## Solution proposée

- Une étape **Tests** dans la bande, entre Production et Sécurité, quand le
  projet a un testeur. Elle est verte sur une suite verte, rouge sur une
  suite rouge, active pendant qu'elle tourne.
- Une carte **TESTEUR** dans le fil, après chaque passage du codeur. Elle
  porte le résumé (`1 error in 2.32s`) et, dépliée, les erreurs que le codeur
  reçoit. Une suite rouge dit en clair « retour au codeur, sans revue ».

## Critères d'acceptation

- [ ] Un test de `StageStrip` vérifie qu'un `test_result` rouge rend l'étape
      Tests en échec, et un vert la rend terminée
- [ ] Un test de `StageStrip` vérifie que l'étape Tests n'apparaît pas pour
      un run qui ne reçoit aucun `test_result`
- [ ] Un test de `FilDuRun` vérifie qu'un `test_result` ajoute une carte
      TESTEUR, avec le résumé dans son en-tête
- [ ] Un test vérifie qu'une carte TESTEUR rouge affiche « retour au codeur,
      sans revue »
- [ ] Les couleurs restent celles d'ADR-026

## Dépendances

Aucune. Le backend émet déjà `test_result` avec `passed`, `output_summary`
et `errors` (`pipeline_stages.py`) : vérifier ces noms au premier tour.