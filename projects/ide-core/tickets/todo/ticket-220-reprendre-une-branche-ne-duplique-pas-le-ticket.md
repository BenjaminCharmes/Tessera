---
id: ticket-220
title: "Reprendre une branche de ticket ne duplique pas le fichier du ticket"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-09-28
---

# ticket-220 — Reprendre une branche ne duplique pas le ticket

## Objectif

Un run qui reprend une branche existante laisse exactement un fichier pour son ticket, dans le dossier de son statut réel.

## Contexte

L'orchestrateur passe le ticket en `in-progress` (il déplace `todo/…` vers `in-progress/…`) **avant** de basculer sur la branche. Si la branche existe déjà, elle apporte sa propre copie du ticket, par exemple dans `blocked/`. On se retrouve avec deux fichiers. `_find_file` prend le premier, les changements de statut suivants en créent un troisième, et au tour 2 `Path.rename` échoue sous Windows sur une cible existante (`FileExistsError: [WinError 183]`). C'est ce qui a interrompu le second run du ticket-213.

## Solution proposée

Deux changements :
- basculer sur la branche avant tout changement de statut, ou relire le ticket après la bascule ;
- dans `update_status`, si plusieurs fichiers portent le même identifiant, garder celui du dossier cible et supprimer les autres, et remplacer `rename` par `replace`.

## Critères d'acceptation

- [ ] Un test : un ticket présent dans `todo/` et dans `blocked/` → après `update_status(in_review)`, un seul fichier, dans `in-review/`
- [ ] Un test : `update_status` vers un dossier où le fichier existe déjà ne lève pas
- [ ] `uv run pytest` passe

## Dépendances

Aucune.
