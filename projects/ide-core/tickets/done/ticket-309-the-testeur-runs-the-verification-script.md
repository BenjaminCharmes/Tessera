---
id: ticket-309
title: "The ide-core testeur runs the verification script, which now works on Windows"
type: chore
status: done
pr_number: null
priority: high
agent: codeur
depends_on: ["ticket-304"]
estimated_days: 0.5
created: 2026-10-02
---

# ticket-309 — Le testeur d'ide-core lance le script de vérification

## Objectif

Mettre en service le script du ticket-304, qui ne tournait pas sous Windows.

## Contexte

Le ticket-304 a livré `scripts/verifier.py`, avec des tests qui remplacent les
commandes par des doublures. Lancé pour de vrai, le script échouait à la
première étape : `No module named pytest`.

- `"python"` désigne, sous Windows, l'interpréteur du système et non celui
  du `.venv`, qui est le seul à avoir pytest et mypy ;
- `"npx"` est un `.cmd`, qu'un `subprocess` sans shell ne trouve pas sous son
  nom court ;
- la sortie était décodée en cp1252, et l'extrait gardait les premières
  lignes, alors que pytest met son résumé à la fin.

Le ticket-304 posait aussi « aucune commande sous `.venv` » comme règle.
Elle était trop large : WDAC refuse les lanceurs générés (`pytest.exe`,
`uvicorn.exe`), pas l'interpréteur du `.venv`, qui est précisément ce que
lance `uv run python`.

Fait à la main : `agents.json` et `CLAUDE.md` sont hors de portée des agents.

## Solution

- `scripts/verifier.py` lance `sys.executable -m pytest` et
  `sys.executable -m mypy`, puis `npx.cmd` sous Windows. Il décode la sortie
  en UTF-8 et garde la fin de la sortie.
- Le test de `test_verifier.py` interdit les lanceurs, et non plus
  l'interpréteur.
- `projects/ide-core/agents.json` : `test_command` devient
  `uv run python ../scripts/verifier.py`, avec `test_timeout_s: 900`.
- **Ce ticket autorise la modification de `projects/ide-core/CLAUDE.md`**
  (règle 5), limitée à la phrase qui décrit ce que lance le testeur.

## Critères d'acceptation

- [x] Lancé depuis `backend/`, `uv run python ../scripts/verifier.py` rend 0
      sur `develop`, en 5 min 38
- [x] `test_verifier.py` passe, avec un test qui vérifie que pytest et mypy
      partent de `sys.executable`
- [x] `projects/ide-core/agents.json` pointe le testeur sur le script
