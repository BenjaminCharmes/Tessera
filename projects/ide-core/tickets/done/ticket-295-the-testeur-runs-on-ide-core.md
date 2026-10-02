---
id: ticket-295
title: "The testeur runs the backend suite on ide-core"
type: chore
status: done
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-01
---

# ticket-295 — Le testeur tourne sur ide-core

## Objectif

Qu'un run d'ide-core qui casse un test hors des fichiers qu'il touche
reparte au codeur, au lieu d'être approuvé puis bloqué par la CI.

## Contexte

Le testeur était désactivé depuis l'origine. Le ticket-212 l'avait laissé
éteint parce que la suite allonge chaque tour. Le 2026-10-01, deux tickets
approuvés ont pourtant échoué en CI pour la même raison : le 264, puis le 285,
ont ajouté une méthode appelée par `pipeline_stages`, sans la donner aux
doublures de git d'autres fichiers de test. Le codeur ne lance que les tests
des fichiers qu'il touche (skill `verifier-mon-travail`), et le reviewer
comme le validateur jugent le diff, pas la suite. La CI l'a vu après
l'approbation : la PR est restée rouge, et le ticket suivant de la file s'est
empilé dessus et en a hérité l'échec (PR #169).

Quatre minutes par tour coûtent moins qu'un cycle approuvé puis perdu.

## Solution proposée

Fait à la main : `agents.json` et `CLAUDE.md` sont hors de portée des agents
(ADR-027, règle 5).

- `pipeline.testeur_enabled: true`, `test_cwd: "../../backend"`,
  `test_command` en `uv run python -m pytest -q -x -m "not integration"`.
  On passe par `python -m` et non par `pytest.exe`, parce que le contrôle
  d'applications Windows refuse les lanceurs `.exe` générés dans un `.venv`
  (os error 4551).
- `test_timeout_s: 600` : la suite prend environ quatre minutes.
- **Ce ticket autorise la modification de `projects/ide-core/CLAUDE.md`**
  (règle 5), limitée au paragraphe « Ce qui tourne réellement sur ce
  projet », qui deviendrait faux.

## Critères d'acceptation

- [x] `projects/ide-core/agents.json` déclare `testeur_enabled: true`,
      `test_cwd` et `test_timeout_s`
- [x] `projects/ide-core/CLAUDE.md` ne dit plus que le testeur est désactivé
- [x] `test_consignes_coherentes.py` passe

## Ce que ça ne fait pas

Le frontend n'est pas lancé par le testeur : `test_command` n'est qu'une
commande, sans shell. La CI le couvre toujours avant le merge.
