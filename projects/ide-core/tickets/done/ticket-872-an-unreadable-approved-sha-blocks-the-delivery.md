---
agent: codeur
created: 2026-11-06
depends_on: []
estimated_days: 0.5
id: ticket-872
pr_number: null
priority: critical
status: done
title: An approved run whose approved SHA could not be read is blocked, never pushed
type: fix
---

# ticket-872 — Un SHA approuvé illisible bloque la livraison

## Objectif

Un run approuvé dont la tête de branche n'a pas pu être lue à l'approbation
ne se pousse pas : il finit en `blocked`, sans push ni PR.

## Contexte

Audit externe du 06/11, vérifié dans le code. `tete_de_branche`
(`backend/src/tessera/services/pipeline/pipeline_approbation.py`) rend `None`
quand `head_sha` lève `GitWorkspaceError`, et `noter_tete_approuvee` transmet
ce `None` comme `approved_sha`. Dans
`backend/src/tessera/services/livraison/livraison.py`,
`_preparer_la_base` ne contrôle la branche que `if approved_sha is not None` :
sans SHA, la livraison continue et pousse ce qu'elle trouve. C'est l'inverse
d'ADR-039 (une porte qui ne peut juger refuse), et la docstring du module
promet déjà que la livraison « refuses to go further than it can prove ».

## Solution proposée

Dans `LivraisonService.livrer_phase_1`, quand `approuve` est vrai et
`approved_sha` est `None`, s'arrêter avant le rebase avec un `Livraison`
dont `arret` dit que l'approbation n'est liée à aucun commit lisible — même
forme que l'arrêt de `branche_modifiee`. Pas de push, pas de PR. Le run non
approuvé reste inchangé.

Les doubles de tests qui n'ont pas de `head_sha` (le `getattr` de
`tete_de_branche`) et attendaient une livraison doivent recevoir un
`head_sha` : c'est le comportement verrouillé que l'audit relève.

## Critères d'acceptation

- [ ] Un test de `backend/tests/test_livraison_sha_approuve.py` vérifie que
      `livrer_phase_1(approuve=True, approved_sha=None, …)` rend un `Livraison`
      avec un `arret` non vide et `pr_number is None`, et que le double git
      n'a reçu aucun push.
- [ ] Un test vérifie qu'un run non approuvé (`approuve=False`,
      `approved_sha=None`) garde son comportement actuel.
- [ ] Le texte de l'`arret` cite l'absence de SHA approuvé lisible.
- [ ] La docstring de `pipeline_approbation.py` décrit le refus effectif.

## Dépendances

Aucune.

## Estimation

Une demi-journée.

## Risques

Des tests de bout en bout du pipeline utilisent des doubles d'espace de
travail sans `head_sha` : les adapter, sans affaiblir le refus.