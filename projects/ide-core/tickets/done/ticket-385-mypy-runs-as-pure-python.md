---
id: ticket-385
title: "mypy is installed as pure Python, below 1.19, because Smart App Control blocks its compiled extensions"
type: chore
status: done
pr_number: null
priority: critical
agent: codeur
depends_on: []
estimated_days: 0.1
created: 2026-10-08
---

# ticket-385 — mypy s'installe en Python pur, sous 1.19

## Objectif

Que la vérification du backend (`scripts/verifier.py`, testeur du pipeline)
puisse lancer mypy sur cette machine.

## Contexte

Le 2026-10-08 vers 08:20 UTC, chaque run ide-core a échoué au testeur sur
`ImportError: DLL load failed while importing base64: Une stratégie de
contrôle d'application a bloqué ce fichier`. Le journal Code Integrity de
Windows (événement 3118, « Smart App Control Block ») montre le refus de
`librt/base64.cp311-win_amd64.pyd`, extension non signée chargée par
`mypy/ipc.py` depuis mypy 1.19. Le fichier n'avait pas changé depuis la
veille, où mypy fonctionnait : c'est la décision de Smart App Control qui a
changé. Une roue compilée de mypy 1.18.2 est bloquée de la même façon
(`type_visitor`).

Ce ticket est fait à la main : le testeur du pipeline ne peut pas vérifier un
correctif de mypy tant que mypy ne démarre pas.

## Solution retenue

- `backend/pyproject.toml` : `mypy>=1.10.0,<1.19` (pas de dépendance à
  `librt`) et `[tool.uv] no-binary-package = ["mypy"]` (construit depuis ses
  sources, sans mypyc, donc sans aucune extension compilée).
- `backend/uv.lock` régénéré : seuls changent mypy (2.1.0 → 1.18.2), et le
  retrait de `librt` et `ast-serialize`.

## Critères d'acceptation

- [x] `uv run python -m mypy --version` répond `mypy 1.18.2 (compiled: no)`
- [x] `uv run python -m mypy src` passe sur tout le backend (109 fichiers, 77 s)
- [x] La suite backend passe

## Ce que ça ne fait pas

- Ne touche pas aux projets pilotés (affut, vigie, habit-tracker… ont aussi
  mypy 2.x avec `librt`) : chacun se corrige dans son propre dépôt.
- Ne désactive pas Smart App Control.
