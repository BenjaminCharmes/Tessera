---
agent: codeur
created: 2026-10-12
depends_on: []
estimated_days: 0.5
id: ticket-401
pr_number: null
priority: high
status: done
title: A chained test command reports the step that failed, not the last summary of
  the whole output
type: fix
---

# ticket-401 — Une commande de test enchaînée rend compte de l'étape en échec

## Objectif

Que le journal et le codeur voient l'étape qui a échoué, avec sa propre
sortie, quand une `test_command` enchaîne plusieurs outils.

## Contexte

`TestRunnerService.run_tests` (`backend/src/tessera/services/test_runner.py`)
découpe la `test_command` en étapes (`decouper`), s'arrête à la première
étape en échec, puis passe à `_parse_output` la sortie de **toutes** les
étapes mises bout à bout.

Signalé par la session qui pilote affut le 2026-10-12, à 07:59 UTC
(ticket-021, trois tours « tests rouges », bloqué). La commande enchaînait
vitest, puis pytest :
- vitest passait ; pytest échouait sur `test_docs_match_code.py` ;
- le journal disait pourtant à chaque tour « testeur: Tests  171 passed
  (171) », le résumé de vitest ;
- `pytest -q` écrit sa ligne de résumé sans bandeaux
  (`1 failed, 455 passed in 3.21s`), et la priorité « bandeau pytest » du
  ticket-393 ne la reconnaît pas : la priorité « vitest » l'emporte ;
- l'architecte n'a jamais vu l'échec réel : tours 2 et 3 en 18 s, sans
  correction.

## Solution proposée

1. Quand une étape échoue, `_parse_output` ne reçoit que la sortie de
   **cette** étape. Le résumé est préfixé par sa commande et son code de
   sortie : « étape `uv --directory backend run python -m pytest -q`
   (exit 1) — 1 failed, 455 passed in 3.21s ».
2. `_extract_summary_line` reconnaît aussi la ligne de résumé de `pytest -q`,
   sans bandeaux (`N failed`, `N passed`, `N error(s)` suivis de
   `in X.XXs`), avant la ligne vitest.
3. `failure_details` (ticket-393) est extrait de la sortie de l'étape en
   échec. Si rien de structuré n'y est trouvé (une étape lint ou tsc, par
   exemple), il contient les 60 dernières lignes de cette sortie.
4. Quand toutes les étapes passent, rien ne change.

## Critères d'acceptation

- [ ] Un test de `backend/tests/test_test_runner.py` fait tourner une commande de deux étapes, la première affichant un résumé vitest « Tests 171 passed (171) » et finissant en 0, la seconde affichant « 1 failed, 455 passed in 3.21s » et finissant en 1, et vérifie que `output_summary` contient la commande de la seconde étape, `exit 1` et `1 failed, 455 passed`
- [ ] Un test de `backend/tests/test_test_runner.py` vérifie que `_extract_summary_line` reconnaît « 1 failed, 455 passed in 3.21s » sans bandeaux
- [ ] Un test de `backend/tests/test_test_runner.py` vérifie qu'une étape en échec sans sortie structurée (lint) donne un `failure_details` qui contient ses dernières lignes, et aucune ligne de l'étape précédente
- [ ] Un test de `backend/tests/test_test_runner.py` vérifie qu'une commande dont toutes les étapes passent garde le résumé actuel

## Dépendances

Aucune.

## Estimation

0,5 jour.

## Ce que ça ne fait pas

- Ne change pas `scripts/verifier.py` d'ide-core, qui est une seule étape.