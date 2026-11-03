---
agent: codeur
created: 2026-10-13
depends_on: []
estimated_days: 0.5
id: ticket-413
pr_number: 396
priority: high
status: done
title: A run on a project that delivers on its own is refused upfront when GitHub
  is not configured for it
type: fix
---

# ticket-413 — Refuser d'emblée un run qui ne pourra pas être livré

## Objectif

Qu'un projet déclaré en `autonomy: pr` ou `merge` sans GitHub configuré ne
dépense pas un run complet pour découvrir, à la livraison, qu'il ne peut
rien pousser.

## Contexte

Le 2026-10-13, la file de `curio` (créé depuis le gabarit, `autonomy: merge`)
a codé, testé, audité et validé le ticket-001 en deux tours, puis s'est
arrêtée à la livraison : « GitHub n'est pas configuré pour ce projet : il
faut un GITHUB_TOKEN et un dépôt distant lié »
(`services/github_workflow.py`). Le dépôt existait, mais `agents.json` ne
déclarait pas `github_remote`. La file entière s'est interrompue, et il a
fallu ouvrir la PR à la main.

La condition est connue dès le `POST /api/v1/orchestrator/run`
(`routers/orchestrator.py`, `run_pipeline`) : `load_project` donne
`github_remote`, `settings.github_token` dit si un jeton existe, et
`agents.json` déclare l'autonomie.

## Solution proposée

- Dans `run_pipeline`, avant `RUN_REGISTRY.ouvrir` : si l'autonomie du projet
  est `pr` ou `merge` et qu'il manque `github_remote` ou le jeton, répondre
  **422** avec un message qui nomme ce qui manque et comment le corriger
  (« déclare `github_remote` dans agents.json » / « renseigne GITHUB_TOKEN »).
- Rien ne change pour `autonomy: commit` : ces projets ne poussent pas.
- Le projet n'est pas réservé : un second essai après correction passe.

## Critères d'acceptation

- [ ] Un test vérifie qu'un `POST /orchestrator/run` sur un projet `merge`
      sans `github_remote` renvoie 422 avec un message citant `github_remote`
- [ ] Un test vérifie qu'un projet `pr` avec `github_remote` mais sans jeton
      renvoie 422 avec un message citant `GITHUB_TOKEN`
- [ ] Un test vérifie qu'un projet `commit` sans `github_remote` démarre
      normalement (202)
- [ ] Un test vérifie qu'après un refus 422, le projet n'est pas marqué
      occupé (`RUN_REGISTRY.projet_occupe` faux)

## Dépendances

Aucune.

## Ce que ça ne fait pas

- Ne vérifie pas que le jeton a réellement accès au dépôt : c'est un appel
  réseau, et la livraison le dit déjà clairement.