---
id: ticket-241
title: "La commande de test déclare son dossier et son délai"
type: feat
status: done
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-29
---

# ticket-241 — La commande de test déclare son dossier et son délai

## Objectif

Permettre à un projet de déclarer, dans la section `pipeline` d'`agents.json`,
le dossier d'où sa commande de test se lance (`test_cwd`) et le temps qu'elle a
pour finir (`test_timeout_s`).

## Contexte

`projects/ide-core/CLAUDE.md` l'explique : les tests de ce dépôt vivent dans
`backend/` et `frontend/`, au-dessus du dossier du projet, et
`TestRunnerService` lance sa commande depuis le dossier du projet, sans shell.
Aucune `test_command` ne peut donc atteindre `../../backend`, et le testeur
reste désactivé. Même en l'atteignant, la suite backend prend environ 250 s
contre un délai figé à 120 s : elle finirait en timeout à chaque tour.

Les services d'ADR-042 ont déjà un `cwd`, borné au périmètre par
`resoudre_le_cwd`. La commande de test n'a pas de raison d'avoir une autre
règle.

## Solution proposée

- `AgentPipelineConfig` gagne `test_cwd: str | None` et `test_timeout_s: int | None`.
- `TestRunnerService(cwd=…, timeout=…)` : le routeur le construit avec ces
  valeurs, avant le run, donc figées comme le reste de la politique.
- Le dossier se résout par `resoudre_le_cwd` : hors périmètre, la commande ne
  démarre pas, et le résultat le dit (`demarree=False`), sans lever.

Ce ticket **n'active pas** le testeur sur ide-core : le faire change la durée
de chaque run. C'est une décision à prendre à part.

## Critères d'acceptation

- [ ] `test_test_runner.py` vérifie que la commande est lancée dans le dossier déclaré par `cwd`, résolu depuis le projet
- [ ] `test_test_runner.py` vérifie qu'un `cwd` qui sort du périmètre rend un résultat `demarree=False` qui nomme le `cwd`
- [ ] `test_test_runner.py` vérifie que le délai déclaré au constructeur s'applique quand `run_tests` n'en reçoit pas
- [ ] `routers/orchestrator.py` passe `test_cwd` et `test_timeout_s` de la config au `TestRunnerService`
- [ ] Ce ticket **modifie `projects/ide-core/CLAUDE.md`** : le paragraphe qui dit qu'aucune `test_command` ne peut atteindre `../../backend` nomme désormais `test_cwd`

## Ce que ça ne fait pas

- Pas de réglage dans l'UI : les deux clefs s'écrivent dans `agents.json`.
- Pas de liste de commandes avec dépendances : une commande suffit pour
  aujourd'hui.
