---
id: ticket-893
title: "The Agent SDK moves to 0.2.179, which ships a Windows wheel again"
type: chore
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-11-09
---

# ticket-893 — Le SDK Agent passe en 0.2.179, qui publie de nouveau un wheel Windows

## Objectif

Sortir Tessera du SDK `claude-agent-sdk` 0.2.159, figé depuis le 03/10, pour
retrouver le CLI embarqué courant.

## Contexte

Le ticket-322 a monté le SDK en 0.2.159 et pas plus loin : 0.2.157 et 0.2.160
à 0.2.163 n'avaient aucun wheel `win_amd64`. Sans wheel, uv construit depuis le
sdist, sans `claude.exe`, et le SDK refuse le `claude.CMD` du PATH.
`backend/tests/test_agent_sdk_windows_wheel.py` verrouille ce point sur
`backend/uv.lock`.

Signalé par la session Vigie le 09/11 (radar de la semaine 2026-W45) et vérifié
sur PyPI le même jour : 0.2.177 (03/11), 0.2.178 (04/11) et 0.2.179 (06/11)
publient tous un wheel `win_amd64`, avec macOS et Linux.

## Solution proposée

- `backend/pyproject.toml` : `claude-agent-sdk>=0.2.179`.
- `uv lock --upgrade-package claude-agent-sdk` depuis `backend/`, pour que
  `uv.lock` porte 0.2.179 et son wheel `win_amd64`, sans monter d'autre paquet.
- Lire les notes de version entre 0.2.159 et 0.2.179 sur ce que Tessera appelle
  (`ClaudeAgentOptions`, hooks `PreToolUse`, `resume`, serveurs MCP en
  processus) et adapter le code seulement si une signature a changé.

## Critères d'acceptation

- [ ] `backend/pyproject.toml` exige `claude-agent-sdk>=0.2.179`.
- [ ] `backend/uv.lock` porte `claude-agent-sdk` en 0.2.179 avec un fichier
      `win_amd64` ; `test_agent_sdk_windows_wheel.py` reste vert sur ce lock.
- [ ] Le diff de `backend/uv.lock` ne change la version d'aucun autre paquet que
      `claude-agent-sdk` et ses dépendances directes nouvelles ou montées.
- [ ] Le rapport du codeur liste les changements de l'API du SDK entre 0.2.159
      et 0.2.179 qui touchent un appel de Tessera, ou dit qu'il n'y en a aucun.

## Dépendances

Aucune.

## Estimation

Une demi-journée.

## Risques

Le nouveau SDK ne sert qu'après `uv sync --extra dev` et un redémarrage du
backend, faits à la main hors de toute file. Le script de phase 0
d'isolation copie `claude.exe` depuis le venv : après la montée, il faudra le
recopier dans `C:\ProgramData\Tessera\bin`.

## Ce que ça ne fait pas

- Ne monte pas le SDK d'Affût ni de Vigie : un ticket par projet, après celui-ci.
- Ne change aucun modèle d'`agents.json`.
