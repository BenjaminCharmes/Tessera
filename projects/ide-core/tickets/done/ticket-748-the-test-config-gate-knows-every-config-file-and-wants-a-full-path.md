---
agent: codeur
created: 2026-11-03
depends_on: []
estimated_days: 1
id: ticket-748
pr_number: 863
priority: high
status: done
title: The test configuration gate knows every configuration file and wants a full
  path
type: fix
---

# ticket-748 — La porte de configuration des tests connaît tous les fichiers et veut un chemin complet

## Objectif

Un diff qui désarme les tests par un fichier de configuration est toujours signalé, et un
ticket ne couvre que les fichiers qu'il nomme vraiment.

## Contexte

Audit du 30/10 (relecture du 03/11), ticket-725 : `_NOMS_SIGNALES` et `fichiers_non_nommes`
(`backend/src/tessera/services/config_tests_touchee.py`).
- Ignorés (vérifié) : `pytest.ini`, `mypy.ini` (qui priment sur `pyproject.toml`) et
  `frontend/vite.config.ts` — or la configuration vitest de ce dépôt vit dans son bloc
  `test:`. La porte est inerte pour vitest sur ide-core.
- « Nommé » veut dire « le nom de base apparaît dans le ticket » : un ticket qui cite
  `frontend/src/x/vitest.config.ts` couvre `frontend/vitest.config.ts`.

## Solution proposée

- Ajouter `pytest.ini`, `tox.ini`, `setup.cfg`, `mypy.ini`, `.mypy.ini`, `.coveragerc`,
  `vite.config.*`, `vitest.workspace.*`.
- Un fichier n'est couvert que si son chemin complet depuis la racine du dépôt figure dans
  le ticket.
- La règle de `contraintes.md` qui liste ces fichiers est complétée sous `## Proposées`.

## Critères d'acceptation

- [ ] Un test vérifie qu'un diff qui crée `backend/pytest.ini` sur un ticket qui ne le nomme
      pas est signalé
- [ ] Un test vérifie qu'un diff qui modifie `frontend/vite.config.ts` est signalé
- [ ] Un test vérifie qu'un ticket citant `frontend/src/x/vitest.config.ts` ne couvre pas
      `frontend/vitest.config.ts`, et qu'un ticket citant `frontend/vite.config.ts` le couvre
- [ ] `projects/ide-core/memory/contraintes.md` porte sous `## Proposées` la liste complétée