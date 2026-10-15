---
agent: codeur
created: 2026-10-15
depends_on: []
estimated_days: 0.25
id: ticket-459
pr_number: 473
priority: low
status: done
title: Ticket status folders stay in git when they are empty
type: chore
---

# ticket-459 — Les dossiers de statut survivent vides

## Objectif

`tickets/todo/` existe toujours dans un clone, même quand tous les tickets
sont faits.

## Contexte

Vu deux fois le 15/10 : sur make-your-call, et sur ide-core (l'écriture des
tickets 451–453 a échoué faute de dossier `tickets/todo/`). Un dossier vide
ne vit pas dans git.

## Solution proposée

- Un `.gitkeep` dans chaque dossier de statut (`todo`, `in-progress`,
  `in-review`, `done`, `blocked`) de `projects/ide-core/tickets/` et du
  gabarit utilisé par `backend/src/tessera/services/project_from_template.py`.
- Le chargement des tickets ignore `.gitkeep`.

## Critères d'acceptation

- [ ] `projects/ide-core/tickets/todo/.gitkeep` existe
- [ ] Un test vérifie qu'un projet créé depuis le gabarit a
      `tickets/todo/.gitkeep`
- [ ] Un test vérifie qu'un dossier contenant seulement `.gitkeep` donne
      zéro ticket sans erreur