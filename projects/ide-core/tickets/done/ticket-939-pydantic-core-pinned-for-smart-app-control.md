---
agent: codeur
created: 2026-11-12
depends_on: []
estimated_days: 0.1
id: ticket-939
pr_number: null
priority: high
status: done
title: "pydantic-core is pinned to a version Smart App Control lets load"
type: chore
---

# ticket-939 — pydantic-core épinglé sur une version que Smart App Control laisse charger

## Objectif

Que le backend redémarre sur ce PC : depuis le 12/11 au matin, Smart App
Control refuse la DLL de `pydantic-core` 2.50.4 (« DLL load failed while
importing _pydantic_core : une stratégie de contrôle d'application a bloqué ce
fichier », Code Integrity 3118). Plus rien n'importe pydantic : ni le
backend, ni pytest, ni `scripts/prochain_numero.py`.

## Contexte

Le ticket-920 a monté pydantic de 2.13.4 à 2.14.3, qui exige `pydantic-core`
2.50.4. Le blocage est par fichier, selon sa réputation, comme mypy le 08/10
(ticket-385) et rpds-py le 12/10. Versions essayées le 12/11 dans un
environnement jetable : 2.46.4, 2.46.5, 2.50.0, 2.50.1, 2.50.2 et 2.50.3
passent ; 2.48.0 et 2.50.4 sont refusées. pydantic 2.14.2 exige 2.50.2.

## Critères d'acceptation

- [x] `backend/pyproject.toml` ajoute `pydantic-core==2.50.2` à
      `constraint-dependencies`, avec un commentaire qui dit pourquoi.
- [x] `backend/uv.lock` résout `pydantic` 2.14.2 et `pydantic-core` 2.50.2.
- [x] `import pydantic` réussit dans le `.venv` du backend après `uv sync`.
- [x] La suite backend passe.

## Ce que ça ne fait pas

- Ne revient pas en 2.13 : 2.14.2 garde les correctifs mineurs du 920.
- Ne lève pas l'épinglage : à revoir quand une version plus récente passera.
