---
agent: codeur
created: 2026-11-06
depends_on: []
estimated_days: 0.5
id: ticket-873
pr_number: null
priority: high
status: todo
title: Agent subprocesses receive no GitHub credentials
type: fix
---

# ticket-873 — Les agents ne reçoivent aucun identifiant GitHub

## Objectif

Le sous-processus d'un agent ne peut ni pousser ni appeler `gh` en écriture
avec les identifiants de l'utilisateur, même s'il contourne le garde lexical
de `Bash`.

## Contexte

Audit externe du 06/11. Le garde git (ADR-067) est lexical :
`G=git; $G push` ou `"g""it" push` passent (ADR-031 l'assume : il attrape une
erreur, pas une évasion). Mais `env_du_sous_processus`
(`backend/src/tessera/services/providers/env_sdk.py`) transmet `GITHUB_TOKEN`
aux agents, et le CLI hérite aussi des identifiants stockés par `gh`
(son dossier de configuration) et par le gestionnaire d'identifiants de git.
Un contournement du garde a donc de quoi agir.

Le push et les PR de la livraison sont faits par le backend lui-même, hors de
cet environnement : ils ne sont pas concernés.

## Solution proposée

Dans `env_du_sous_processus` :
- vider `GITHUB_TOKEN` et `GH_TOKEN` comme les autres secrets (retirer
  `_TRANSMIS`) ;
- pointer `GH_CONFIG_DIR` vers un dossier vide propre à Tessera, sous
  `IDE_STATE_DIR`, créé s'il manque : `gh` n'y trouve aucune session ;
- neutraliser l'aide d'identifiants de git par l'environnement :
  `GIT_CONFIG_COUNT=1`, `GIT_CONFIG_KEY_0=credential.helper`,
  `GIT_CONFIG_VALUE_0=` (vide), et `GIT_TERMINAL_PROMPT=0`.

Les lectures `gh` d'un dépôt privé par un agent cessent de fonctionner :
c'est accepté, `git log` et les fichiers suffisent.

## Critères d'acceptation

- [ ] Un test de `backend/tests/test_env_sdk.py` vérifie que l'environnement
      rendu porte `GITHUB_TOKEN` et `GH_TOKEN` vides.
- [ ] Un test vérifie que `GH_CONFIG_DIR` désigne un dossier existant et vide.
- [ ] Un test vérifie que `GIT_CONFIG_COUNT`, `GIT_CONFIG_KEY_0`
      (`credential.helper`), `GIT_CONFIG_VALUE_0` (vide) et
      `GIT_TERMINAL_PROMPT` (`0`) sont posés.
- [ ] Le commentaire « le vider se décide après mesure » disparaît de
      `env_sdk.py`, remplacé par la raison du vidage.

## Dépendances

Aucune.

## Estimation

Une demi-journée.

## Risques

Un agent qui lisait une PR par `gh` perd cette lecture sur un dépôt privé.
