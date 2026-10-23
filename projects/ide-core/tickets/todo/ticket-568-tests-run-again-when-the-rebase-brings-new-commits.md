---
id: ticket-568
title: "The tests run again before the push when the rebase brought new base commits"
type: feat
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-23
plan: true
---

# ticket-568 — Les tests repassent quand le rebase a ramené des commits

## Objectif
Qu'un run ne pousse pas une branche dont les tests ont été verts **avant**
le rebase, mais qui casse **après**, quand la base a avancé pendant le run.

## Contexte
Le 23/10, le ticket-544 (cliquet de longueur) était vert au testeur. Pendant
son run, le ticket-542 a été mergé sur develop et a ajouté une ligne à
`services/documentation.py`. La livraison (`services/livraison.py`) a rebasé
la branche sur develop puis poussé sans repasser les tests : la CI a vu
714 lignes pour un plafond de 713, la PR #616 est restée ouverte et la file
s'est arrêtée. Le testeur local l'aurait vu en six minutes.

## Solution proposée
Dans la phase 1 de livraison, après le rebase et avant le push : si le
rebase a ramené au moins un commit de la base (la base distante a avancé
depuis la création de la branche), relancer la `test_command` du projet. Si
elle échoue, pas de push : le run finit comme un run dont la livraison
s'arrête (`Livraison.arret`, ADR-030), avec la sortie du test dans le
journal. Si la base n'a pas bougé, rien ne change (pas de coût).

## Critères d'acceptation
- [ ] Un test, avec des doubles, montre qu'un rebase qui ramène un commit de la base relance la `test_command` avant le push
- [ ] Un test montre qu'un rebase sans nouveau commit de la base ne relance pas la `test_command`
- [ ] Un test montre qu'une `test_command` rouge après rebase empêche le push et renseigne `Livraison.arret`
- [ ] `memory/pipeline-log.md` reçoit une ligne qui dit que les tests ont été relancés après rebase, et leur issue

## Ce que ça ne fait pas
- Ne relance ni le reviewer ni le validateur : le diff du ticket n'a pas
  changé, seule la base a bougé.
