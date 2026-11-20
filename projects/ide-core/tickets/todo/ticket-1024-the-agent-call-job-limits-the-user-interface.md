---
id: ticket-1024
title: "The agent call job limits the user interface"
type: feat
status: todo
priority: medium
agent: codeur
depends_on: []
preuve_reelle: true
---

# ticket-1024 — Le job d'un appel agent limite l'interface utilisateur

## Objectif

Poser, en défense en profondeur d'ADR-089, les restrictions `JOB_OBJECT_UILIMIT_*`
sur le job de chaque appel du compte agent, sans toucher aux jobs de services.

## Contexte

`creer_groupe()` (`services/noyau/groupe_de_processus.py`) ne pose que
`KILL_ON_JOB_CLOSE`. `LanceurWindows` s'en sert pour chaque appel (ticket-943).
`SetInformationJobObject` accepte la classe `JobObjectBasicUIRestrictions` (4).

## À faire

- `creer_groupe(restrictions_ui: bool = False)` : si vrai, pose `HANDLES`,
  `READCLIPBOARD`, `WRITECLIPBOARD`, `GLOBALATOMS`, `DESKTOP`,
  `SYSTEMPARAMETERS`, `DISPLAYSETTINGS` et `EXITWINDOWS`. Un échec de pose
  ferme le job et lève : l'agent ne démarre pas sans (ADR-037).
- `LanceurWindows._lancer` l'appelle avec `restrictions_ui=True` ; les services
  (ADR-042) gardent le défaut.

## Critères d'acceptation

- [ ] `creer_groupe` accepte `restrictions_ui`, défaut `False`, et le combine
      avec `KILL_ON_JOB_CLOSE`.
- [ ] Un test avec un faux `kernel32` vérifie la classe 4 et les huit drapeaux
      quand `restrictions_ui` est vrai, et leur absence sinon.
- [ ] Un test vérifie que l'échec de la pose ferme le job et lève.
- [ ] `pytest` et `mypy` passent ; aucun service ne change de comportement.

## Preuve réelle

Sur la machine, script hors dépôt dans `~/.tessera/worktrees/manuel/` : un
processus lancé par le lanceur ne lit ni n'écrit le presse-papiers (accès
refusé) ; le CLI Claude, `node` et `uv run pytest` démarrent encore avec ces
restrictions. Un processus qui échoue au démarrage (`0xC0000142`) rend le
ticket `blocked`.

## Ce que ça ne fait pas

- Ne ferme ni `SendInput` ni la capture d'écran : c'est le ticket-1023.
- Ne remplace pas la station dédiée : ADR-089 impose les deux.
