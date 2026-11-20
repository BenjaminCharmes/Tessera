---
agent: codeur
created: 2026-11-11
depends_on: []
estimated_days: 0.1
id: ticket-938
pr_number: null
priority: medium
status: done
title: "Evening triage of proposed lessons and rules, two ADRs archived to fit the budget"
type: chore
---

# ticket-938 — Tri du soir des leçons et règles proposées

## Objectif

Trancher les leçons et règles proposées le 11/11, que le superviseur a
renvoyées « À toi » (PR #1057 à #1060).

## Ce qui est fait (à la main, tri délégué par Benjamin)

- Leçon du ticket-933 (données de test qui déclenchent le contrôle de traces
  professionnelles) : en vigueur. Le piège est tombé deux fois le même jour
  (913, 933).
- Leçons des tickets 931 et 934 : écartées. La première ne vaut que pour son
  cas ; la seconde redit la leçon déjà en vigueur sur la mesure des fichiers.
- Règle ADR-084 (un appel d'agent qui change un fichier protégé, un hook ou la
  config git met le run en `blocked`) : acceptée, resserrée, sous « Portes qui
  échouent fermées ». Le contrôle tourne, rendu sûr par le ticket-937.
- Règles ADR-083 et ADR-085 : laissées sous `## Proposées` tant
  qu'`AGENT_USER` n'est renseigné sur aucun projet.
- Budget de `contraintes.md` (12 000 caractères hors proposées) : la règle
  ADR-006/007 (`ProjectLoader` et nom du projet), détail d'implémentation tenu
  par ses tests, est retirée ; ADR-006 et ADR-007 passent dans
  `decisions-archive.md`.

## Critères d'acceptation

- [x] `test_consignes_coherentes.py` et les tests des leçons et contraintes
      passent.
