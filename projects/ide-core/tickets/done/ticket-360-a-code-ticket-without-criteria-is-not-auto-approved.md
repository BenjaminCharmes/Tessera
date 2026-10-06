---
agent: codeur
created: 2026-10-06
depends_on:
- ticket-359
estimated_days: 0.5
id: ticket-360
pr_number: null
priority: high
status: done
title: A feat or fix ticket without acceptance criteria is refused, not auto-approved
type: fix
---

# ticket-360 — Un ticket de code sans critère n'est plus approuvé d'office

## Objectif

Le validateur échoue fermé (ADR-039) quand un ticket `feat` ou `fix` n'a
aucun critère d'acceptation : rien n'a été vérifié, ça ne peut pas valoir
approbation.

## Contexte

`ValidatorService.validate` (`backend/src/tessera/services/validator.py`)
rend `APPROVED` dès que la liste de critères est vide. Combiné au défaut du
ticket-359, les 8 tickets du projet `serpent` ont été livrés et mergés le
2026-10-05 sans validation, sans que rien ne le signale ailleurs que dans
`pipeline-log.md`.

Un ticket `chore` ou `docs` sans critère reste légitime (bookkeeping,
mise à jour de doc) : la règle ne vise que le code.

## Solution proposée

Le validateur reçoit le type du ticket. Pour `feat`, `fix` et `refactor`,
une liste vide rend `CHANGES_REQUESTED` avec un message qui dit quoi faire
(« ajouter une section `## Critères d'acceptation` au ticket »). Pour les
autres types, le comportement actuel est conservé.

## Critères d'acceptation

- [ ] Un test vérifie qu'un ticket `feat` sans critère obtient `CHANGES_REQUESTED`, sans appel au provider
- [ ] Un test vérifie qu'un ticket `fix` sans critère obtient `CHANGES_REQUESTED`
- [ ] Un test vérifie qu'un ticket `chore` sans critère obtient toujours `APPROVED`
- [ ] Le message rendu pour un ticket de code sans critère nomme la section `## Critères d'acceptation`

## Ce que ça ne fait pas

- Ne relance pas le codeur en boucle : le refus passe par le chemin habituel d'un `CHANGES_REQUESTED` du validateur.
- Ne touche pas au planificateur (ticket-359).

## Dépendances

ticket-359 : sans lui, tout ticket planifié serait refusé.

## Risques

Des tickets existants de projets importés peuvent ne pas avoir de critères :
ils seront refusés au prochain run. C'est voulu, mais à annoncer.