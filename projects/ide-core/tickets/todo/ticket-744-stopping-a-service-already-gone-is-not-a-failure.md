---
id: ticket-744
title: "Stopping a service whose process is already gone is not a failure"
type: fix
status: todo
pr_number: null
priority: low
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-11-03
---

# ticket-744 — Arrêter un service dont le processus a déjà disparu n'est pas un échec

## Objectif

L'arrêt d'un service ne journalise plus un échec quand le service est bel et bien
arrêté.

## Contexte

03/11, 13:09 : trois `arret_service_echoue` avec `"erreur": ""` à l'arrêt des services
d'Affût, qui se sont pourtant arrêtés. Dans `ProcessRegistry._terminer`
(`backend/src/tessera/services/process_registry.py`), `tuer_l_arbre` tue l'arbre, puis
`processus.terminate()` vise un processus déjà mort et lève (`ProcessLookupError`, au
message vide) : `except Exception` le journalise en échec, sans même nommer le type.

## Solution proposée

- Un `ProcessLookupError` après `tuer_l_arbre` est un arrêt réussi : on attend la fin
  du processus et on ne journalise pas d'échec.
- Les autres exceptions restent `arret_service_echoue`, avec le type de l'exception
  dans `erreur` même quand son texte est vide.

## Critères d'acceptation

- [ ] Un test vérifie, avec des doubles, qu'un `terminate()` qui lève
      `ProcessLookupError` ne journalise pas `arret_service_echoue`
- [ ] Un test vérifie qu'une autre exception journalise `arret_service_echoue` avec
      le nom du type dans `erreur`, même quand son message est vide

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

Aucun : l'arrêt lui-même ne change pas.
