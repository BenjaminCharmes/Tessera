---
id: ticket-351
title: "verifier.py runs the backend and frontend checks side by side"
type: refactor
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: ["ticket-348"]
estimated_days: 0.5
created: 2026-10-05
---

# ticket-351 — `verifier.py` lance les vérifications backend et frontend côte à côte

## Objectif

Raccourcir le tour du testeur d'ide-core, environ six minutes aujourd'hui, en
faisant tourner les deux chaînes indépendantes en même temps.

## Contexte

`scripts/verifier.py` exécute `STEPS` l'une après l'autre : pytest, mypy
(dans `backend/`), puis tsc, eslint, vitest (dans `frontend/`), et s'arrête au
premier échec (tickets 295 et 304). Les deux chaînes ne partagent rien : la
durée totale est leur somme alors qu'elle pourrait être leur maximum.

Le ticket-348 borne le nombre de suites simultanées sur la machine : une suite
qui occupe deux cœurs pendant son créneau ne retombe pas dans la contention
qu'il corrige.

## Solution proposée

1. Deux chaînes : `BACKEND_STEPS` (pytest puis mypy) et `FRONTEND_STEPS`
   (tsc, eslint, vitest), chacune séquentielle et arrêtée à son premier échec.
2. Les deux chaînes tournent en parallèle (threads ou `subprocess.Popen`, au
   choix), chacune capturant sa propre sortie — jamais entrelacée.
3. Le code de sortie est non nul si l'une des deux échoue. Le rapport cite
   chaque étape en échec, avec son nom et l'extrait de sortie déjà produit par
   `_extract_errors`, chaîne backend d'abord.
4. Les consignes de la docstring restent : jamais de lanceur `.exe`, outils
   Python via `sys.executable -m`, `npx.cmd` sous Windows.

## Critères d'acceptation

- [ ] `verifier.py` définit `BACKEND_STEPS` et `FRONTEND_STEPS`
- [ ] Un test de `backend/tests/test_verifier.py` montre, avec des étapes factices qui durent,
      que les deux chaînes se chevauchent dans le temps
- [ ] Un test montre qu'un échec dans la chaîne backend n'empêche pas la
      chaîne frontend d'aller au bout, et que le code de sortie est non nul
- [ ] Un test montre qu'un échec en tête de chaîne empêche les étapes
      suivantes de **cette** chaîne
- [ ] Un test montre que le rapport nomme chaque étape en échec quand les
      deux chaînes échouent

## Dépendances

ticket-348 : sans créneau partagé, doubler les processus d'une suite
aggraverait la contention entre projets.

## Estimation

Une demi-journée.

## Risques

Sortie illisible si les deux chaînes écrivent en direct : tout capturer, puis
imprimer à la fin.
