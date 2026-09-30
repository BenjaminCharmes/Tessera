---
id: ticket-272
title: "Lockfiles are summarized, not pasted, in the diff given to reviewing agents"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-09-30
---

# ticket-272 — Les lockfiles ne noient plus le diff relu par les agents

## Objectif

Que le reviewer, l'audit et le validateur voient le vrai changement d'un run,
même quand ce run ajoute ou modifie un fichier de verrouillage.

## Contexte

Constaté le 2026-09-30 sur `carriere` (ticket-008) et `freelance`
(ticket-005) : les deux runs ont été bloqués après trois tours. Le validateur :
« le diff se limite à `backend/uv.lock` et est tronqué avant tout changement
frontend ». Le vrai changement — quatre lignes dans `package.json` et
`vite.config.ts` — était correct ; il était coupé par la troncature, derrière
des milliers de lignes de `uv.lock`.

Le diff relu vient de `GitWorkspaceService.diff_depuis_base`
(`services/git_workspace.py`), puis est tronqué avant d'entrer dans les
prompts.

## Solution proposée

- Pour les fichiers de verrouillage connus — `uv.lock`, `package-lock.json`,
  `pnpm-lock.yaml`, `yarn.lock`, `poetry.lock`, `Cargo.lock` — le diff relu ne
  porte qu'une ligne de résumé par fichier (`<chemin> : fichier de
  verrouillage modifié, N lignes ajoutées, M supprimées`), pas leur contenu.
- La liste vit à un seul endroit, constante nommée.
- Le commit, lui, n'est pas concerné : les lockfiles restent commités en
  entier.

## Critères d'acceptation

- [ ] Un test montre que le diff relu d'un changement qui touche `uv.lock` et
      `package.json` contient le contenu de `package.json` et une seule ligne
      de résumé pour `uv.lock`.
- [ ] Un test montre que le résumé donne le nombre de lignes ajoutées et
      supprimées du lockfile.
- [ ] Un test montre qu'un fichier nommé `uv.lock` dans un sous-dossier
      (`backend/uv.lock`) est aussi résumé.

## Dépendances

Aucune.

## Estimation

Une demi-journée. Backend uniquement.

## Risques

Un changement de dépendance devient moins visible pour l'audit sécurité : le
résumé doit rester présent, et `package.json` / `pyproject.toml`, eux,
restent en entier — c'est là qu'une dépendance s'ajoute.
