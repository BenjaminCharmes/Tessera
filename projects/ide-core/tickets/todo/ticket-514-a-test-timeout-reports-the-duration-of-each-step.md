---
id: ticket-514
title: "A test timeout reports how long each step took, so the step that overran is named"
type: feat
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-19
---

# ticket-514 — Un délai de test dépassé dit combien de temps chaque étape a pris

## Objectif
Qu'un run bloqué par « testeur : délai dépassé » dise quelle étape de la
`test_command` a débordé, sans avoir à la rejouer à la main.

## Contexte
`TestRunnerService.run_tests` (`backend/src/tessera/services/test_runner.py`)
découpe la `test_command` en étapes et les enchaîne sous un délai global
(`test_timeout_s`, qui démarre une fois le créneau de test obtenu). Chaque
étape terminée est gardée dans `EtapeTest` (commande et code de sortie), mais
pas sa durée. À l'expiration, le `TestResult` ne dit que
« Timeout après Ns — <commande complète> ».

Le 19/10, le ticket-034 de Devinoo a été bloqué « délai dépassé deux fois »
(limite 420 s). Il a fallu chronométrer à la main chacune des six étapes
(install 6 s, lint 28 s, typegen 10 s, tsc 30 s, vitest 59 s, check:build
123 s) pour comprendre que la suite entière frôle la limite dès que la machine
est chargée.

## Solution proposée
- `EtapeTest` gagne `duree_ms`, mesurée pour chaque étape.
- À l'expiration, le résultat liste les étapes terminées avec leur durée,
  puis l'étape en cours au moment de la coupure, avec le temps qu'elle avait
  déjà consommé.
- La ligne de journal du testeur (`memory/pipeline-log.md`) sur un délai
  dépassé reprend ce détail sous une forme courte :
  `testeur: délai dépassé (420 s) — install 6 s, lint 28 s, …, check:build coupé après 190 s`.
- Ce que voit le codeur au tour suivant contient la même liste.

## Critères d'acceptation
- [ ] Dans `test_runner.py`, `EtapeTest` porte un champ `duree_ms` renseigné pour chaque étape terminée
- [ ] Un test vérifie qu'à l'expiration, le résultat nomme l'étape coupée et le temps qu'elle avait consommé
- [ ] Un test vérifie que les étapes terminées avant la coupure sont listées avec leur durée
- [ ] La ligne de journal d'un délai dépassé contient la durée de chaque étape (un test le vérifie)
- [ ] Les tests existants de `test_runner` passent sans modification de leurs assertions

## Dépendances
Aucune.

## Estimation
Une demi-journée.

## Risques
Rester court dans le journal : une étape par entrée, au plus une ligne.
