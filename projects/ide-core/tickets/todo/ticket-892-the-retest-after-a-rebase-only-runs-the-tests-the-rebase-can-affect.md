---
id: ticket-892
title: "The retest after a rebase only runs the tests the rebase can affect"
type: chore
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-11-09
plan: true
---

# ticket-892 — Le retest après rebase ne lance que les tests que le rebase peut toucher

## Objectif

Qu'un ticket qui ne touche que le frontend ne repaye pas la suite pytest
entière après son rebase sur `develop`.

## Contexte

Le 06/11, le ticket-877 (frontend seul) a été rebasé avant sa livraison, et le
retest a relancé pytest en entier : 1 288 s, pour un diff sans fichier Python.
`scripts/verifier.py` sait pourtant borner pytest : `--impact base` pour le
testeur, et le retest après rebase ajoute son propre `--impact <sha>`, le
dernier l'emportant (ticket-793). Quelque part entre
`services/livraison/retest_apres_rebase.py`, `livraison_rebase.py` et
`verifier.py`, le bornage n'a pas joué : soit le `<sha>` passé couvre tout ce
que `develop` a reçu depuis la base (et non ce que le rebase a changé pour la
branche), soit `fichiers_de_test_impactes` renvoie `None` sur ce diff et tout
tourne.

Le tour de plan doit d'abord **établir la cause** en lisant le journal du
ticket-877 (`projects/ide-core/memory/pipeline-log.md`) et le code, avant de
corriger. Aucune hypothèse de ce ticket n'est un fait.

## Solution proposée

- Mesurer : un test qui reproduit la situation (branche touchant `frontend/`
  seulement, `develop` avancé de commits backend) et vérifie la liste de
  fichiers de test que `fichiers_de_test_impactes` renvoie pour le `<sha>`
  réellement passé par le retest.
- Corriger ce que la mesure montre : le `<sha>` donné par le retest, ou la
  sélection dans `verifier.py`, pour que le retest d'un diff sans Python ne
  lance que les tests globaux du dépôt (ceux listés comme « jugent tout le
  dépôt », ticket-793).
- Journaliser dans `pipeline-log.md` la liste ou le nombre de fichiers de test
  que le retest a lancés, pour qu'un prochain écart se lise sans rejouer.

## Critères d'acceptation

- [ ] Un test de `verifier.py` vérifie qu'un diff limité à `frontend/` donne,
      pour pytest, la seule liste des tests globaux (pas `None`).
- [ ] Un test de `retest_apres_rebase.py` vérifie que l'option `--impact`
      ajoutée au retest porte la référence attendue par la cause établie au plan
      (la base avant rebase ou le SHA que le plan désigne), et que cette
      référence est journalisée.
- [ ] Une ligne du journal de run dit combien de fichiers de test le retest a
      sélectionnés ; un test le vérifie avec un double de journal.
- [ ] Le diff ne modifie ni `conftest.py`, ni `[tool.pytest*]`, ni `scripts`
      de `package.json` (ADR-072).

## Dépendances

Aucune.

## Estimation

Un jour.

## Risques

Un bornage trop étroit laisse passer une régression backend révélée par le
rebase : les tests globaux restent toujours lancés, et la CI de la PR reste la
porte complète.

## Ce que ça ne fait pas

- Ne traite pas la durée de l'étape de documentation (16 min le 06/11) : sujet
  distinct, à mesurer séparément.
