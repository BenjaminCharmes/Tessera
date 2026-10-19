---
agent: codeur
created: 2026-10-19
depends_on: []
estimated_days: 0.5
id: ticket-512
pr_number: 560
priority: high
status: done
title: Test commands run with a closed stdin, so no tool can wait for input from the
  backend's console
type: fix
---

# ticket-512 — Les commandes de test tournent avec une entrée standard fermée

## Objectif
Qu'aucun outil lancé par une `test_command` ne puisse rester bloqué en
attendant une saisie sur la console du backend.

## Contexte
`TestRunnerService._lancer` (`backend/src/tessera/services/test_runner.py`)
appelle `asyncio.create_subprocess_exec` avec `stdout` et `stderr` en `PIPE`,
mais sans `stdin` : chaque commande hérite de l'entrée standard du backend,
qui est une console Windows quand il est lancé par `scripts/tessera.ps1`.

Le 19/10, la file Devinoo s'est figée deux fois de la même manière (08:28 et
10:59 UTC). Les deux fois, c'était le premier passage de tests après un
redémarrage du backend, sur une branche reprise. `pnpm install` lance le
postinstall `prisma generate`, qui ne rend jamais la main (processus encore
vivants 55 minutes plus tard). Le même `pnpm install`, lancé dans un terminal,
finit en 94 ms. Une entrée standard héritée et jamais fermée est la différence
d'environnement la plus probable. Le ticket-507 borne la durée d'un tel
blocage au `test_timeout_s` ; ce ticket en retire la cause probable.

## Solution proposée
Lancer chaque étape de test avec `stdin=asyncio.subprocess.DEVNULL`. Vérifier
les autres lancements de commandes non interactives du pipeline (commande de
test, vérification de reprise, services sans port s'ils passent par la même
fonction) et leur appliquer la même règle. `services/lancement.py` est
partagé avec `ProcessRegistry` : ne rien changer pour les services
interactifs.

## Critères d'acceptation
- [ ] Dans `test_runner.py`, `_lancer` passe `stdin=asyncio.subprocess.DEVNULL` à `create_subprocess_exec`
- [ ] Un test lance une commande qui lit l'entrée standard (par exemple `python -c "import sys; print(repr(sys.stdin.read()))"`) et vérifie qu'elle se termine aussitôt avec une entrée vide
- [ ] Les tests existants de `test_runner` passent sans modification de leurs assertions

## Dépendances
Aucune.

## Estimation
Une demi-journée.

## Risques
Si la cause était ailleurs (réseau, télémétrie de Prisma), le blocage peut se
reproduire : le ticket-507 le bornera alors, et la piste suivante est
`CHECKPOINT_DISABLE=1` dans l'environnement de la commande Devinoo, côté
projet.