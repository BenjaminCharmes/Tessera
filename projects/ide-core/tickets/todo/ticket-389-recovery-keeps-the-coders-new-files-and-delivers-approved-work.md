---
id: ticket-389
title: "Startup recovery keeps the files the coder created, and an approved but undelivered ticket is flagged for delivery"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: ["ticket-377"]
estimated_days: 0.5
created: 2026-10-09
---

# ticket-389 — La reprise garde les fichiers neufs du codeur et signale un ticket approuvé non livré

## Objectif

Qu'un ticket repris au démarrage ait sur sa branche tout le travail du
codeur, et qu'un ticket déjà approuvé ne soit pas traité comme un ticket à
refaire.

## Contexte

La reprise au démarrage (`backend/src/tessera/services/reprise_orphelin.py`,
tickets 369, 375, 377) ne commite que les fichiers déjà suivis (`git add
--update`), pour ne jamais embarquer un fichier étranger (autre projet,
brouillon). Deux trous constatés le 2026-10-09 après le redémarrage du PC à
07:38 UTC :

1. **Fichiers neufs du codeur perdus** (affut, ticket-020, signalé par la
   session qui pilotait affut) : le commit de reprise a laissé hors commit
   `backend/tests/test_docs_match_code.py`, un fichier créé par le codeur ; la
   branche portait un travail incomplet, commité à la main avant le merge.
2. **Ticket approuvé non livré remis à zéro** (vigie, ticket-014, signalé par
   la session qui pilote vigie) : approuvé et commité la veille à 15:42 UTC,
   coupé avant sa livraison ; la reprise l'a traité comme un run inachevé. Il
   a été livré à la main.

## Solution proposée

1. Ajouter au commit de reprise les fichiers **non suivis** du projet dont la
   date de modification est postérieure au `started_at` du run soldé, hors
   chemins ignorés par git et hors dépôts imbriqués (un dossier contenant un
   `.git`). Un fichier plus ancien que le run reste hors commit, comme
   aujourd'hui.
2. Si le run soldé avait atteint « APPROVED » (événement ou statut `done` de
   la fiche sur sa branche), ne pas remettre la fiche en `todo` : la laisser
   `done`, et journaliser
   `[<ticket>] approuvé mais non livré : livraison à reprendre`.

## Critères d'acceptation

- [ ] Un test de `backend/tests/test_reprise_run_orphelin.py` crée un fichier non suivi après le `started_at` du run soldé et vérifie qu'il figure dans le commit de reprise
- [ ] Un test de `backend/tests/test_reprise_run_orphelin.py` vérifie qu'un fichier non suivi antérieur au `started_at` du run n'entre pas dans le commit de reprise
- [ ] Un test de `backend/tests/test_reprise_run_orphelin.py` vérifie qu'un dépôt git imbriqué récent n'entre pas dans le commit de reprise
- [ ] Un test de `backend/tests/test_reprise_run_orphelin.py` vérifie qu'un ticket dont la fiche est `done` sur sa branche n'est pas remis en `todo`, et qu'une ligne « approuvé mais non livré » est écrite dans `memory/pipeline-log.md`

## Dépendances

ticket-377 (fiche du ticket toujours présente sur la branche reprise).

## Estimation

0,5 jour.

## Risques

Un fichier étranger créé pendant le run (un brouillon de l'utilisateur dans
le projet) entrerait dans le commit de reprise : il reste sur la branche du
ticket, jamais sur la base, et se voit dans la PR.

## Ce que ça ne fait pas

- Ne livre pas automatiquement le ticket approuvé : la livraison reste à
  relancer.
