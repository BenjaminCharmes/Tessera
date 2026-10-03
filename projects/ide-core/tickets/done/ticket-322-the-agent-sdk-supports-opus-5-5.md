---
id: ticket-322
title: "The Claude Agent SDK moves to 0.2.159, whose bundled Claude Code supports claude-opus-5-5"
type: chore
status: done
pr_number: 240
priority: high
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-02
---

# ticket-322 — Le SDK Agent passe en 0.2.159

## Objectif

Qu'un rôle déclaré sur `claude-opus-5-5` tourne, au lieu d'échouer en 400 dès
son premier appel.

## Contexte

Le 2026-10-02, le codeur du ticket-018 de `carriere`, déclaré sur
`claude-opus-5-5`, a échoué au bout de 3 secondes :

```
API Error: 400 Claude Code 2.1.259 does not support this model;
version 2.1.280 or newer
```

Tessera dépend de `claude-agent-sdk>=0.2.152` (`backend/pyproject.toml:15`).
Le SDK embarque sa propre copie de Claude Code, en version 2.1.259 dans la
0.2.152. Opus 5.5 exige au moins la 2.1.280. La 0.2.163 embarque la 2.1.286.

`claude-sonnet-5-5` fonctionne déjà avec la 2.1.259, vérifié le même jour :
le CLI journalise `unrecognized_model`, mais c'est bien ce modèle qui répond.

## Solution proposée

- `backend/pyproject.toml` : `claude-agent-sdk>=0.2.163`, et `uv.lock` mis à
  jour en conséquence.
- Un test d'intégration, marqué `integration` et donc hors de la suite
  courante, appelle `claude-opus-5-5` par le provider `agent_sdk` et vérifie
  que `model_usage` le nomme.

## Critères d'acceptation

- [x] ~~`backend/pyproject.toml` exige `claude-agent-sdk>=0.2.163`~~ —
      `>=0.2.159`, voir « Écart » ci-dessous
- [x] ~~`backend/uv.lock` résout `claude-agent-sdk` en 0.2.163 ou plus~~ —
      résout en 0.2.159
- [x] Un test marqué `integration` appelle `claude-opus-5-5` et vérifie le
      modèle rapporté par `model_usage`
- [x] Les tests existants de `providers/agent_sdk.py` passent

## Écart : 0.2.159 et non 0.2.163

Les versions 0.2.160 à 0.2.163 ne publient **aucun wheel `win_amd64`** sur
PyPI. Sous Windows, uv construit alors le SDK depuis le sdist, sans le
`claude.exe` embarqué ; le SDK se rabat sur le `claude.CMD` du PATH et refuse
de l'exécuter (`CLIConnectionError: Refusing to execute batch script`). Chaque
run aurait échoué dès son premier appel.

La 0.2.159 a un wheel Windows et embarque Claude Code 2.1.281, au-dessus des
2.1.280 qu'exige Opus 5.5 : le test d'intégration le vérifie en réel.
`test_agent_sdk_windows_wheel.py` refuse un `uv.lock` dont la version du SDK
n'a pas de wheel Windows — c'est lui qui arrêtera une prochaine montée
aveugle.

## Ce que ça ne fait pas

Le `.venv` local n'est pas mis à jour : `uv sync` se lance à la main après le
merge, backend arrêté. Ça ne change aucun `agents.json`. Le codeur et l'architecte de `carriere`
sont passés sur `claude-sonnet-5-5` en attendant (PR carriere #20) : les
remettre sur Opus 5.5 reste un choix, à faire après ce ticket.

## Risques

Une mise à jour du SDK peut changer le format des messages (`ResultMessage`,
`model_usage`, hooks). Les tests de `agent_sdk.py` et de `git_guard` doivent
passer sans modification.
