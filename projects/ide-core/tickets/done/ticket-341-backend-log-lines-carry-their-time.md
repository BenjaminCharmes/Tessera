---
id: ticket-341
title: "Every backend log line carries its UTC time"
type: fix
status: done
pr_number: 260
priority: medium
agent: codeur
depends_on: []
estimated_days: 0.25
created: 2026-10-05
---

# ticket-341 — Chaque ligne du journal du backend porte son heure

## Objectif

Qu'une ligne de `backend/logs/tessera.log` se date sans recoupement.

## Contexte

Le 2026-10-05, l'enquête sur le ticket-034 de démineur (ticket-340) a trouvé
au journal la ligne `base_ref_initialisee_locale`, preuve d'un fetch raté,
sans pouvoir la dater par rapport au merge du 033 : le formateur JSON ne
sortait que `level`, `logger`, `message` et les `extra`. La chronologie a dû
être reconstruite depuis les reflogs git.

## Solution proposée

`_JsonFormatter` ajoute en tête un champ `ts`, l'heure de création de la
ligne en UTC, ISO 8601 à la milliseconde (`2026-10-05T08:47:03.120Z`).

## Critères d'acceptation

- [x] Un test vérifie que `ts` vaut l'heure de création de la ligne, en UTC à
      la milliseconde, et qu'il est la première clé

## Dépendances

Aucune.

## Estimation

0,25 jour.
