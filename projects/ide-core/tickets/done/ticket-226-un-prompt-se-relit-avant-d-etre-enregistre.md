---
id: ticket-226
title: "Un prompt d'agent se relit en diff avant d'être enregistré"
type: feat
status: done
pr_number: null
priority: low
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-09-29
---

# ticket-226 — Relire un prompt avant de l'enregistrer

## Objectif

Modifier le prompt d'un agent depuis l'IDE montre ce qui change et demande une confirmation, parce qu'un prompt pilote tous les runs suivants.

## Contexte

La vue Agents permet déjà d'éditer et d'enregistrer un prompt, natif compris (`AgentDetail`, `PUT /agents/{role}`, ticket-079). Mais « Enregistrer » écrit tout de suite : rien ne montre ce qui va changer, alors qu'une modification change le comportement de tous les runs de tous les projets qui utilisent ce rôle.

## Solution proposée

« Enregistrer » ouvre d'abord un diff ligne à ligne entre le prompt enregistré et le brouillon, avec deux boutons, « Confirmer » et « Annuler ». Le `PUT` ne part qu'après « Confirmer ». Frontend uniquement.

## Critères d'acceptation

- [x] Un test Vitest : « Enregistrer » affiche les lignes retirées et ajoutées, sans appeler `api.agents.updatePrompt`
- [x] Un test Vitest : « Confirmer » appelle `api.agents.updatePrompt` avec le brouillon
- [x] Un test Vitest : « Annuler » garde le brouillon et n'appelle pas l'API
- [x] Un brouillon identique au prompt enregistré n'ouvre pas de diff et n'envoie rien (test Vitest)

## Dépendances

Aucune.
