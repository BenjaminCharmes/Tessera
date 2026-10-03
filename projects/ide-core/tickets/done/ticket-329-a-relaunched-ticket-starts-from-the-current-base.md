---
agent: codeur
created: 2026-10-02
depends_on: []
estimated_days: 1
id: ticket-329
plan: true
pr_number: null
priority: high
status: done
title: A relaunched ticket rebuilds its branch on the current base, and finds its
  ticket file wherever the last run left it
type: fix
---

# ticket-329 — Un ticket relancé repart de la base actuelle

## Objectif

Qu'un ticket relancé ne reprenne pas en silence une branche bâtie sur une base
dépassée, et qu'il ne se perde pas dans un dossier de statut.

## Contexte

Le 2026-10-02, sur `carriere` :

- le ticket-024, relancé, a repris son ancienne branche locale.
  `GitWorkspaceService.create_branch` (`services/git_workspace.py`, vers la
  ligne 334) est idempotent : une branche existante est reprise telle quelle.
  Celle-ci partait d'un `main` antérieur aux tickets 022, 025 et 026. Le
  ticket a été « approuvé » en un tour sur son ancien travail, puis sa
  livraison a buté sur des conflits (migrations SQL, icônes, routes) ;
- le ticket-027, relancé, a échoué sur « Ticket introuvable ». Le run
  précédent, coupé net, l'avait déplacé dans `tickets/blocked/` sans commit.
  Une fois ce dossier non suivi retiré, la branche n'avait plus de fichier
  ticket.

## Solution proposée

- Quand une branche de ticket existe déjà et que sa base (sa fusion avec la
  base distante) est en retard sur la base actuelle, le run la rejoue sur la
  base actuelle (`rejouer_sur`) avant d'y travailler. En cas de conflit, il
  annule le rejeu et repart d'une branche neuve depuis la base, l'ancienne
  étant renommée `stale/…` pour ne rien perdre.
- Le ticket se cherche dans tous les dossiers de statut, puis sur la base
  distante, avant de conclure « introuvable ».

## Critères d'acceptation

- [ ] Un test sur un dépôt temporaire vérifie qu'une branche de ticket dont la
      base est en retard est rejouée sur la base actuelle avant le tour du
      codeur
- [ ] Un test vérifie qu'un rejeu en conflit renomme l'ancienne branche en
      `stale/…` et repart d'une branche neuve depuis la base
- [ ] Un test vérifie qu'un ticket absent de la branche mais présent sur la
      base distante est retrouvé, sans « Ticket introuvable »
- [ ] Un test vérifie qu'une branche à jour est reprise sans changement

## Dépendances

Aucune.