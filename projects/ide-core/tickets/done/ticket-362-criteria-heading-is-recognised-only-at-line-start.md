---
agent: codeur
created: 2026-10-06
depends_on: []
estimated_days: 0.25
id: ticket-362
pr_number: null
priority: high
status: done
title: The acceptance-criteria heading is recognised only at the start of a line
type: fix
---

# ticket-362 — Le titre des critères n'est reconnu qu'en début de ligne

## Objectif

Qu'un ticket qui cite le titre de sa section de critères dans sa prose garde
ses critères : le validateur doit les juger, pas les perdre.

## Contexte

`_extract_criteria` (`backend/src/tessera/services/pipeline_text.py`) repère
la section avec `_CRITERIA_HEADING.search(line)`. `search` trouve le motif
n'importe où dans la ligne. Une phrase du Contexte qui cite le titre entre
backticks ouvre donc la section ; le titre de niveau 2 suivant (« Solution
proposée ») la referme aussitôt, avant les vrais critères. Résultat : une
liste vide.

Constaté le 2026-10-06 sur les tickets 359 et 360 : le validateur a répondu
« Aucun critère d'acceptation — approbation automatique » alors que chacun en
portait quatre. Depuis le ticket-360, une liste vide sur un ticket `feat` ou
`fix` fait refuser le run : le même défaut bloquerait désormais ces tickets à
chaque tour.

Le même `search` saute aussi un critère dont le texte cite le titre (les
critères 1 et 3 du ticket-359 le faisaient).

## Solution proposée

Ancrer le motif en début de ligne : n'accepter qu'une ligne qui *commence*
par le titre de niveau 2 (`^##\s*…`, via `match` ou une ancre), insensible à
la casse comme aujourd'hui. Aucun autre comportement ne change.

## Critères d'acceptation

- [ ] Un test de `backend/tests/test_pipeline_text.py` donne à `_extract_criteria` un corps dont le Contexte cite le titre de section entre backticks, suivi d'un autre titre puis de la vraie section avec deux critères, et vérifie que les deux critères sont rendus
- [ ] Un test de `backend/tests/test_pipeline_text.py` vérifie qu'un critère dont le texte cite le titre de section entre backticks figure dans le résultat
- [ ] Les tests existants de `backend/tests/test_pipeline_text.py` passent sans modification
- [ ] `_CRITERIA_HEADING` dans `backend/src/tessera/services/pipeline_text.py` ne reconnaît le titre qu'en début de ligne

## Dépendances

Aucune.

## Estimation

0,25 jour.

## Risques

Un ticket dont le titre de section est indenté ne serait plus reconnu. Aucun
ticket existant ne l'indente ; le format est celui de `_build_body`
(ticket-359) et du skill `new-ticket`.

## Ce que ça ne fait pas

- Ne touche pas au validateur ni au refus des tickets sans critère (ticket-360).
- Ne repasse pas sur les tickets déjà livrés.