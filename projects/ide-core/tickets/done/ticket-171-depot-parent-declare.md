---
id: ticket-171
title: "Le panneau Git propose d'imbriquer un dépôt dans celui de Tessera"
type: fix
status: done
pr_number: 20
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-25
---

# ticket-171 — Un projet qui travaille dans le dépôt parent le déclare

## Objectif

Qu'un projet en `git_root: ancestor` ne soit pas annoncé comme non versionné.

## Contexte

Le panneau Git d'`ide-core` affiche :

> **Ce projet n'est pas versionné.** Sans dépôt git, un pipeline ne crée ni
> branche ni commit : le travail des agents reste dans l'arbre, sans trace.
> Il se trouve dans le dépôt `C:\…\tessera`, qui n'est pas le sien.
> **[ Initialiser un dépôt git ]**

C'est faux, et le bouton est dangereux.

`ide-core` déclare `"git_root": "ancestor"` — ADR-028, qui lève explicitement
le refus d'ADR-024 pour le projet bootstrap : il construit l'IDE, donc il
travaille volontairement dans le dépôt qui le contient, et son travail est
dans `backend/` et `frontend/`, au-dessus de lui.

`get_git_status` ne regarde que `is_own_repository`. La déclaration qui rend
cette situation **normale** n'est jamais lue. Le panneau conclut donc à une
anomalie, et propose d'y remédier en créant un dépôt **imbriqué dans celui de
Tessera** — précisément ce qu'ADR-024 a été écrit pour empêcher.

Un utilisateur qui clique casse son propre dépôt, en suivant une instruction de
l'IDE.

## Solution proposée

1. `GitStatusResponse` porte `uses_parent_repository`, lu depuis la politique
   du projet (`PolitiqueRun.dans_le_depot_parent`).
2. Le panneau, dans ce cas, dit que le projet travaille dans le dépôt qui le
   contient — et n'offre aucun bouton d'initialisation.
3. `init_git` **refuse** sur un projet en `ancestor`. Le bouton disparaît,
   mais l'endpoint reste appelable : une garde qui dépend de l'interface n'en
   est pas une (ADR-027).

## Critères d'acceptation

- [ ] `GET /git/status` rend `uses_parent_repository: true` sur un projet
      déclarant `git_root: ancestor`, `false` sinon
- [ ] `POST /git/init` refuse en 422 sur un tel projet, en nommant `git_root`
- [ ] Le panneau n'affiche ni « n'est pas versionné » ni le bouton
      d'initialisation dans ce cas
- [ ] Un projet ordinaire sans dépôt garde le message et le bouton d'avant
- [ ] `uv run pytest`, `npx vitest run`, `tsc` et `eslint` passent

## Dépendances

Aucune.

## Estimation

Moins d'une journée.

## Risques

Aucun pour les projets ordinaires : la déclaration est absente chez eux, et
`dans_le_depot_parent` est faux — le comportement d'avant tient.
