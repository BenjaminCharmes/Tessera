---
agent: codeur
created: 2026-11-09
depends_on: []
estimated_days: 0.5
id: ticket-893
pr_number: 995
priority: medium
status: done
title: The Agent SDK moves to 0.2.179, which ships a Windows wheel again
type: chore
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
## Rapport du codeur : changements d'API entre 0.2.159 et 0.2.179

Source : `CHANGELOG.md` du dépôt du SDK, de 0.2.159 à 0.2.178 (il n'a pas de
section 0.2.179). Aucun changement ne touche un appel de Tessera
(`ClaudeAgentOptions`, hooks `PreToolUse`, `resume`, serveurs MCP en
processus) : aucun code n'a été adapté.

- 0.2.160 : correctif, les tours de suite n'échouent plus après des
  sous-agents en arrière-plan avec hooks, `can_use_tool` ou serveurs MCP.
- 0.2.166 : ajouts de types (sorties de hooks, `SystemInitData`) ; le type de
  `SandboxSettings.ignoreViolations` devient `dict[str, list[str]]`, que
  Tessera n'utilise pas.
- 0.2.170 : correctif de `get_session_messages` pour les appels d'outils
  parallèles.
- 0.2.177 : option `on_failure` de `HookMatcher`, défaut `"continue"`, donc
  comportement inchangé pour les hooks de Tessera.
- Autres versions : seul le CLI embarqué monte (2.1.281 vers 2.1.318).
## Rapport du codeur : périmètre du diff de `backend/uv.lock`

`git diff --numstat` : 8 lignes ajoutées, 8 retirées. Ce sont, dans le bloc
`claude-agent-sdk`, la ligne `version` (0.2.159 vers 0.2.179), la ligne
`sdist`, cinq lignes de wheels (macOS arm64 et x86_64, deux manylinux,
`win_amd64`), et le `specifier` de `tessera` (`>=0.2.159` vers `>=0.2.179`).
Aucune autre ligne `version` n'a bougé : aucun autre paquet n'est touché, et
les dépendances du SDK (`anyio`, `jsonschema`, `mcp`, `sniffio`) sont les mêmes.