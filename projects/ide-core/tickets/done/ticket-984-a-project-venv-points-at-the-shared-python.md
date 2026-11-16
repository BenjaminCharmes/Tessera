---
agent: codeur
depends_on:
- ticket-981
id: ticket-984
preuve_reelle: true
priority: medium
status: done
title: A project venv points at the shared Python, not at one in a profile
type: fix
---

## Contexte

ADR-086. Un `.venv` créé par `uv` pointe, dans `pyvenv.cfg`, vers le Python
qui l'a fait : sous `%APPDATA%\uv\python`, illisible au compte agent. Le
setup du worktree tourne sous le compte du backend (ADR-085), et ce seul
setup décide où pointe le venv.

## Ce qu'il faut faire

- Le setup du worktree (backend, avant les tests) passe
  `UV_PYTHON_INSTALL_DIR=C:\ProgramData\Tessera\toolchain\python` et
  `UV_PYTHON_PREFERENCE=only-managed` à `uv sync` / `uv venv` quand
  `worktree.compte_agent` est déclaré. Sans compte agent, rien ne change.
- Le cache `uv` reste celui que ADR-085 donne en lecture ; il ne contient pas
  d'interpréteur.
- Chaîne absente : le setup échoue fermé avec un message nommant `agent setup`.

## Critères d'acceptation

- [ ] Test : l'environnement du setup d'un projet à compte agent porte les
      deux variables ; sans compte agent, il ne les porte pas.
- [ ] Test : `home` de `pyvenv.cfg`, sur un venv fabriqué par le setup, est
      sous `toolchain\python`.

## Preuve réelle

Faite par la session ide-core après merge et redémarrage, pas par le
validateur : un projet Python à compte agent passe son étape de test sous `tessera-agent` ; Serpent ticket-009 aussi (non-régression).

## Ce que ça ne fait pas

- N'ouvre aucun droit sur un profil : si un venv existant pointe ailleurs, il
  se recrée, il ne se rend pas lisible.