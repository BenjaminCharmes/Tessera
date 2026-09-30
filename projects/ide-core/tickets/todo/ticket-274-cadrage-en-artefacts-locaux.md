---
id: ticket-274
title: "Design tickets on local-artifact projects show their decisions and tickets to reviewing agents"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
plan: true
depends_on: []
estimated_days: 1
created: 2026-09-30
---

# ticket-274 — Un cadrage sur un projet en artefacts locaux se relit

## Objectif

Qu'un ticket `design` produit sur un projet en mode `artifacts: local` soit
jugé sur ce qu'il a écrit, au lieu d'être refusé faute de diff.

## Contexte

Constaté le 2026-09-30 sur `freelance` (ticket-004, `design`, rôle
`architect`). L'architecte a écrit quatre décisions dans `memory/decisions.md`
et six tickets dans `tickets/todo/`. Le run a été **bloqué après trois tours** :
« le diff soumis se limite au cochage des cases dans `ticket-004` ; aucun des
fichiers réellement porteurs… ».

Le projet déclare `artifacts: local` (ADR-021, ADR-023) : `memory/` et
`tickets/` sont exclus par `.git/info/exclude`. Le diff relu
(`GitWorkspaceService.diff_depuis_base`) ne voit que ce que git suit — donc
**rien** de ce qu'un cadrage produit. Tout ticket `design` sur un tel projet est
condamné au même refus.

## Solution proposée

À concevoir au tour de plan. Piste : quand le projet est en artefacts locaux,
photographier `memory/` et `tickets/` au démarrage du run, et ajouter au
matériau relu (reviewer, validateur ; pas l'audit sécurité, qui porte sur du
code) un diff textuel entre cette photo et l'état de fin de tour, étiqueté
« artefacts locaux, non versionnés ». Rien de ce diff n'entre dans un commit.

## Critères d'acceptation

- [ ] Un test montre que, sur un projet `artifacts: local`, une décision
      ajoutée à `memory/decisions.md` pendant le run figure dans le matériau
      transmis au validateur.
- [ ] Un test montre qu'un ticket créé dans `tickets/todo/` pendant le run y
      figure aussi.
- [ ] Un test montre que ce matériau n'est pas transmis sur un projet
      `artifacts: tracked` (le diff git y suffit).
- [ ] Un test montre qu'aucun fichier de `memory/` ni de `tickets/` n'est
      commité sur un projet `artifacts: local`.

## Dépendances

Aucune.

## Estimation

1 jour. Backend uniquement.

## Risques

Les artefacts locaux peuvent contenir ce qu'on a voulu garder hors du dépôt :
ce matériau part aux agents (comme le reste du contexte projet), jamais dans
un commit, une PR ou un log.
