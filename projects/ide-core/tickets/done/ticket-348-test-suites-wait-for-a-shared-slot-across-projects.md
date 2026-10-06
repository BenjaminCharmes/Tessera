---
agent: codeur
created: 2026-10-05
depends_on: []
estimated_days: 0.5
id: ticket-348
pr_number: 278
priority: high
status: done
title: Test suites wait for a shared slot across projects, and their timeout starts
  once it is granted
type: fix
---

# ticket-348 — Les suites de tests attendent un créneau partagé entre projets

## Objectif

Que plusieurs files lancées sur plusieurs projets ne fassent plus tourner
toutes leurs suites de tests en même temps sur la machine, et qu'une suite qui
attend son tour ne soit pas comptée comme lente.

## Contexte

`RunLock` (`backend/src/tessera/services/run_lock.py`) n'autorise qu'un run
par projet, mais rien ne borne ce qui tourne **entre** projets. Le
2026-10-05, cinq files tournaient en parallèle : chaque testeur lançait sa
suite complète au même moment. Celle d'ide-core (`scripts/verifier.py` :
pytest, mypy, tsc, eslint, vitest) prend environ six minutes machine libre ;
sous cette charge, le ticket-347 a dépassé `test_timeout_s: 900` et son
premier tour a été perdu.

`TestRunnerService` (`backend/src/tessera/services/test_runner.py`) est
instancié à chaque requête (`routers/orchestrator.py`) : un verrou posé sur
l'instance ne protège rien. Le délai part de `start = time.monotonic()` au
lancement de la commande, et `_executer` le décompte étape par étape.

## Solution proposée

1. Un réglage `max_parallel_test_runs: int = 2` dans
   `backend/src/tessera/config.py` (variable `MAX_PARALLEL_TEST_RUNS`).
   0 ou moins désactive la borne.
2. Un `asyncio.Semaphore` **de niveau module**, créé paresseusement au premier
   usage avec la valeur du réglage (pas à l'import : il n'y a pas encore de
   boucle), partagé par tous les `TestRunnerService` du processus.
3. `TestRunnerService.run_tests` prend le créneau **avant** de lancer la
   première étape et le rend en sortie, y compris sur timeout, exception ou
   annulation (`async with`). `start` n'est relevé qu'une fois le créneau
   obtenu : l'attente ne consomme pas le délai.
4. `run_tests` accepte un rappel optionnel `en_attente: Callable[[], Awaitable[None]] | None`,
   appelé une seule fois quand le créneau n'est pas immédiatement disponible.
   `run_tests` de `backend/src/tessera/services/pipeline_stages.py` s'en sert
   pour écrire `[ticket-XXX] testeur: en attente d'un créneau de test` dans le
   `pipeline-log`.

## Critères d'acceptation

- [ ] `config.py` déclare `max_parallel_test_runs` avec 2 pour défaut
- [ ] Un test de `test_test_runner.py` lance trois `run_tests` concurrents
      avec une borne à 1 (commande factice qui dure) et vérifie qu'à aucun
      moment deux commandes ne tournent ensemble
- [ ] Un test de `test_test_runner.py` montre qu'une suite qui a attendu son
      créneau plus longtemps que son `timeout` aboutit quand même : l'attente
      n'est pas décomptée
- [ ] Un test de `test_test_runner.py` montre que le créneau est rendu après
      un timeout : un second `run_tests` démarre ensuite
- [ ] Un test montre que le rappel `en_attente` est appelé quand le créneau
      est pris, et ne l'est pas quand il est libre
- [ ] `pipeline_stages.py` écrit la ligne « testeur: en attente d'un créneau
      de test » dans le `pipeline-log` via ce rappel

## Dépendances

Aucune.

## Estimation

Une demi-journée.

## Risques

- Un sémaphore créé à l'import se lierait à une boucle inexistante, ou à celle
  d'un test précédent : prévoir une fonction de réinitialisation pour les
  tests.
- Borne trop basse : les files s'allongent en attente. D'où le réglage.