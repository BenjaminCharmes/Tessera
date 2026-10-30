---
id: ticket-724
title: "A test configuration change the ticket does not name is refused"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-30
---

# ticket-724 — Un changement de configuration des tests que le ticket ne nomme pas est refusé

## Objectif
Un run ne doit pas pouvoir assouplir la vérification qui le juge sans que le
ticket le demande.

## Contexte
Le 30/10, sur Curio (ticket-070, qui ne touchait que le backend), le codeur a monté
`testTimeout` à 15 s dans `frontend/vitest.config.ts` pour franchir les tours 1
et 2. Le reviewer a reçu l'avertissement d'en tête du ticket-490
(`TITRE_CONFIG_TESTS`, `backend/src/tessera/services/config_tests_touchee.py`) et a
approuvé quand même. La session Curio a livré à la main sans cette modification.
Un avertissement lu par un LLM ne tient pas : il faut une porte.

## Solution proposée
Après le reviewer, si `fichiers_de_config_touches` rend des fichiers et qu'aucun
n'est cité dans le texte du ticket (nom du fichier, ou chemin), le verdict devient
`CHANGES_REQUESTED`. La remarque bloquante nomme les fichiers et dit : « ce ticket ne
demande pas de modifier la configuration des tests : retire ce changement ». Le tour
suivant reçoit cette remarque comme les autres. Un ticket qui nomme le fichier
garde le comportement actuel (avertissement seul).

## Critères d'acceptation
- [ ] `test_unnamed_test_config_change_forces_changes_requested` (dans `backend/tests/test_config_tests_touchee.py` ou un fichier voisin nommé d'après la porte) : un diff qui modifie `vitest.config.ts` sur un ticket qui ne le nomme pas donne `CHANGES_REQUESTED`, avec une remarque qui nomme le fichier, même si le reviewer a approuvé
- [ ] `test_named_test_config_change_keeps_the_review_verdict` : le même diff sur un ticket qui cite `vitest.config.ts` garde le verdict du reviewer
- [ ] `test_no_test_config_change_is_untouched` : un diff sans fichier de configuration de test ne change pas le verdict
- [ ] La porte s'applique aussi au `pyproject.toml` (section pytest ou mypy) et aux `scripts` de `package.json` que la liste existante reconnaît

## Ce que ça ne fait pas
- N'interdit pas de modifier la configuration des tests : un ticket peut le demander
- Ne remplace pas le refus d'écrire le script de `test_command` (ADR-027)
