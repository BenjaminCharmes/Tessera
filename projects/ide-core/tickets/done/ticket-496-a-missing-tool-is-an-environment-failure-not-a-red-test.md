---
agent: codeur
created: 2026-10-17
depends_on: []
estimated_days: 0.5
id: ticket-496
pr_number: 517
priority: medium
status: done
title: A test step whose tool cannot be found is reported as an environment failure,
  not as failing code
type: fix
---

# ticket-496 — Un outil introuvable est une panne d'environnement, pas un test rouge

## Objectif

Quand une étape de test démarre mais que l'outil qu'elle appelle est
introuvable (`tsc`, `vitest`, `next`…), le testeur le dit comme une panne
d'environnement, pour que le codeur ne corrige pas du code qui n'est pas en
cause.

## Contexte

16/10, Devinoo : après le renommage de `projects/make-your-call` en
`projects/devinoo`, les liens de `node_modules` (pnpm les écrit en chemin
absolu) pointaient toujours vers l'ancien dossier. `pnpm tsc`, `vitest` et le
build échouaient faute de module, et le ticket-018 a tourné plusieurs tours de
revue sur un échec que le code ne pouvait pas corriger. Réparé à la main par
`corepack pnpm@10 install --frozen-lockfile --config.confirmModulesPurge=false`.

`test_runner.py` connaît déjà le cas où l'exécutable lui-même manque
(`FileNotFoundError` → `demarree=False`, ticket-157). Mais ici, `pnpm` démarre :
c'est l'outil qu'il appelle qui manque, et la sortie arrive comme un test rouge
ordinaire.

## Solution proposée

1. Une fonction pure, dans un petit module à part (`outil_introuvable.py`), qui
   reconnaît dans la sortie d'une étape en échec qu'un **outil** manque, et non
   un import du code du projet :
   - `ERR_PNPM_RECURSIVE_EXEC_FIRST_FAIL` avec `Command "<x>" not found` ;
   - `sh: <x>: command not found` / `<x>: not found` ;
   - `'<x>' is not recognized as an internal or external command` ;
   - `Cannot find module '…/node_modules/…'` quand le chemin cité est sous
     `node_modules` **et n'existe pas**, ou pointe hors du dossier du projet
     (lien périmé après un renommage).
   Elle rend le nom de l'outil, ou `None`.
2. Dans `TestRunnerService`, une étape en échec reconnue ainsi produit un
   `TestResult` avec `demarree=False` et un `output_summary` qui dit : panne
   d'environnement, outil `<x>` introuvable, réinstaller les dépendances du
   projet ; ce n'est pas un test en échec.
3. Un `Cannot find module` qui vise un fichier du projet (hors `node_modules`)
   reste un test rouge : c'est le code qui est en cause.

## Ce que ça ne fait pas

- Ne réinstalle rien : réparer `node_modules` reste une action humaine ou
  celle d'une session de projet.
- Ne contrôle pas les liens au renommage ou à l'import d'un projet.

## Critères d'acceptation

- [ ] Un test vérifie que la sortie pnpm `Command "tsc" not found` est
      reconnue et rend `tsc`
- [ ] Un test vérifie que `'vitest' is not recognized as an internal or
      external command` est reconnu et rend `vitest`
- [ ] Un test vérifie qu'un `Cannot find module` sur un chemin sous
      `node_modules` situé hors du dossier du projet est reconnu
- [ ] Un test vérifie qu'un `Cannot find module './brand'` (fichier du projet)
      n'est pas reconnu
- [ ] Un test de `TestRunnerService` vérifie qu'une étape reconnue rend
      `demarree=False` et un `output_summary` contenant « panne
      d'environnement »

## Risques

Un faux positif ferait passer un vrai import cassé pour une panne
d'environnement : d'où la restriction à `node_modules` et aux messages de
commande introuvable.