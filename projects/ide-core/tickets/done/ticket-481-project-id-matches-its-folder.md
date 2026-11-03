---
agent: codeur
created: 2026-10-16
depends_on: []
estimated_days: 0.25
id: ticket-481
pr_number: 545
priority: low
status: done
title: A project whose agents.json project_id differs from its folder name is flagged
  at load
type: fix
---

# ticket-481 — Un `project_id` qui ne suit pas le dossier est signalé

## Objectif

Un projet renommé dont `agents.json` garde l'ancien `project_id` est
signalé au chargement, au lieu de passer inaperçu.

## Contexte

devinoo, 16/10 : au renommage `make-your-call` → `devinoo` (dépôt, dossier,
historique), `"project_id"` est resté à `make-your-call` dans `agents.json`.
La session l'a corrigé à la main (PR #37), `agents.json` étant interdit aux
agents.

## Solution proposée

Au chargement d'un projet (`backend/src/tessera/services/project_loader.py`),
si `agents.json` déclare un `project_id` différent du nom du dossier :
journaliser un avertissement et l'exposer dans la vue d'ensemble du projet
(`ProjectOverview`, champ `avertissements`) ; le nom du dossier reste
l'identifiant.

## Critères d'acceptation

- [ ] Un test vérifie l'avertissement quand `project_id` diffère du dossier
- [ ] Un test vérifie l'absence d'avertissement quand ils sont égaux ou que
      `project_id` est absent
- [ ] Un test vérifie que l'identifiant reste le nom du dossier