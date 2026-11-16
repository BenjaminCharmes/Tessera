---
agent: codeur
created: 2026-11-13
depends_on: []
estimated_days: 1
id: ticket-971
pr_number: null
priority: high
status: todo
title: "A test that times out in files the diff does not touch is run again once, alone, before the round is red"
type: fix
---

# ticket-971 — Un test qui expire hors du diff est relancé une fois, seul, avant de rendre le tour rouge

## Objectif

Qu'un test frontend instable sous charge ne coûte plus trois tours à un ticket
qui n'y touche pas, et ne pousse plus le codeur à affaiblir la configuration
des tests pour le faire passer.

## Contexte

Soir du 13/11, cinq files en parallèle. Curio 098 et 100, deux tickets
backend, ont perdu trois tours chacun : le testeur était rouge sur
`App.challenges.test.tsx` et `play-screen.test.tsx` (« Test timed out »).

Le 16/11, trois files en parallèle : ide-core 977 a perdu son dernier tour sur
`StatsView/RecentRunsCard.test.tsx`, fichier hors de son diff, avec
`TestingLibraryElementError: Unable to find an element with the text: Aucun
run ne correspond à « zzz »`. C'est un `findBy` dont le délai propre a
expiré, pas un « Test timed out ». Le même jour, un codeur de Curio a
signalé (signalement fusionné ici, ex-979) que l'étape frontend tombait sur
un fichier différent à chaque tour d'un ticket backend seul
(`review-options`, puis `play-screen`), et que chacun passait relancé seul.
Sur le 100, le codeur a modifié `frontend/vitest.config.ts` (testTimeout,
hookTimeout, maxWorkers) et `test-setup.ts` pour faire passer ces tests : la
porte ADR-072 l'a refusé, à raison, mais le tour était perdu. Kadoomi (172,
176, 180) et Vigie (095, délai du testeur) ont vu la même chose plus tôt.

## Solution proposée

1. Quand une étape de tests vitest ou pytest échoue, le testeur relève les
   fichiers de test en échec dans la sortie (les extracteurs de
   `sortie_de_test.py` les lisent déjà en partie).
2. Si **tous** les échecs sont des expirations (vitest « Test timed out »,
   Testing Library « Unable to find an element » ou « Timed out in waitFor »,
   pytest-timeout « Timeout ») **et** qu'aucun des fichiers en échec, ni le
   code qu'ils testent dans le même dossier, n'est dans le diff du run, ces
   fichiers sont relancés **une fois**, seuls (`vitest run <fichiers>`,
   `pytest <fichiers>`), sous le même limiteur de suites.
3. Verts à la relance : l'étape est verte, et le journal porte
   `tests_instables_relances` (fichiers, durée). Rouges : l'étape reste rouge
   avec la sortie d'origine et celle de la relance.
4. Un échec qui n'est pas une expiration n'est jamais relancé.
5. **La relance n'a lieu que si les tests sont la seule cause de l'échec.**
   `scripts/verifier.py` combine ruff, mypy, mypy-linux, tsc, eslint, vitest
   et pytest dans une seule sortie : une erreur d'un outil statique y paraît
   en section (`mypy :` suivi d'un extrait), sans ligne FAIL. Si la sortie
   contient une section en échec d'un autre outil que vitest ou pytest, ou
   une ligne que le parseur ne sait pas classer, rien n'est relancé et
   l'étape reste rouge (relevé par le reviewer, 16/11, run 92959c84). Un
   diff illisible empêche aussi toute relance (même run).

## Critères d'acceptation

- [ ] Un test : une sortie vitest dont le seul échec est un « Test timed out »
      dans un fichier hors du diff provoque une relance de ce fichier seul ;
      verte, l'étape est verte et `tests_instables_relances` est journalisé.
- [ ] Un test : une sortie vitest dont le seul échec est un
      `TestingLibraryElementError: Unable to find an element` dans un fichier
      hors du diff est relancée de même.
- [ ] Un test : la relance rouge garde l'étape rouge, avec les deux sorties.
- [ ] Un test : un fichier en échec qui est dans le diff n'est pas relancé.
- [ ] Un test : un échec d'assertion (pas une expiration) n'est pas relancé.
- [ ] Un test : la même chose pour une sortie pytest avec une expiration
      pytest-timeout.
- [ ] Un test : une sortie de `verifier.py` qui porte une expiration vitest
      hors du diff **et** une section `mypy :` (ou ruff, tsc, eslint) en
      échec n'est pas relancée, et l'étape reste rouge.
- [ ] Un test : un diff illisible (`diff_depuis_base` qui lève) n'ouvre
      aucune relance.

## Ce que ça ne fait pas

- Ne change pas les délais des tests ni la configuration des projets.
- Ne relance qu'une fois : un test rouge deux fois est rouge.
