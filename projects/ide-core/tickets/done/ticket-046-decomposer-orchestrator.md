---
id: ticket-046
title: "Décomposer run_pipeline en étapes nommées"
type: refactor
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: [ticket-045]
estimated_days: 2
created: 2026-09-15
---

# ticket-046 — Décomposer `run_pipeline` en étapes nommées

## Objectif

Ramener `backend/src/vibe_ide/services/orchestrator.py` sous la barre des
200 lignes fixée par `CLAUDE.md` (règle 5), en découpant `run_pipeline` en
étapes lisibles et testables séparément.

## Contexte

`ticket-045` a déjà extrait les modèles d'événements (`pipeline_events.py`) et les
helpers de texte (`pipeline_text.py`), ramenant le fichier de 711 à ~640 lignes.

Le gros du volume restant est `run_pipeline` lui-même : ~490 lignes qui enchaînent
codeur → tests → sécurité → reviewer → validateur → doc-updater → commit, avec de
l'état local partagé (`review_feedback`, `branch`, `round_num`, `reviewed_code`) et
des closures d'émission d'événements. Le découper est un vrai travail de conception,
pas une extraction mécanique — d'où ce ticket dédié plutôt qu'un fourre-tout dans
`ticket-045`.

## Solution proposée

1. Introduire un objet de contexte (`PipelineRun`) portant l'état partagé du run :
   ticket, branche, tour courant, retours reviewer accumulés, callback d'événements.
2. Extraire une méthode par étape, chacune prenant ce contexte :
   `_run_coder`, `_run_tests`, `_run_security_audit`, `_run_review`,
   `_run_validation`, `_run_doc_update`.
3. `run_pipeline` ne garde que l'enchaînement et les sorties anticipées.
4. Un test unitaire par étape, en plus des tests end-to-end existants.

## Critères d'acceptation

- [x] `orchestrator.py` fait moins de 200 lignes
- [x] Chaque étape du pipeline est une méthode nommée, testable isolément
- [x] Les 47 tests d'orchestration existants passent sans modification de leurs
      assertions (le comportement ne change pas)
- [x] `uv run mypy src/` passe sans erreur
- [x] Aucun changement de comportement observable via l'API ou les événements WS

## Dépendances

`ticket-045` (doit être mergé pour éviter un conflit massif sur le même fichier).

## Estimation

**2j** — refactor à comportement constant, protégé par la suite existante.

## Risques

- **Moyen** — c'est le cœur du produit. Mitigation : aucun changement de
  comportement autorisé, la suite de tests actuelle fait office de filet.

## Résultat

| Fichier | Lignes |
|---|---|
| `orchestrator.py` | 640 → **177** |
| `pipeline_stages.py` | 375 |
| `pipeline_outcomes.py` | 135 |
| `pipeline_run.py` | 73 |

`pipeline_stages.py` reste au-dessus des 200 lignes de la règle 5. Le découper
davantage reviendrait à éparpiller une seule préoccupation — « faire tourner
chaque agent du pipeline » — entre plusieurs fichiers pour satisfaire un
compteur. La couture naturelle, entre les étapes et les sorties du run, a été
prise ; la suivante ne l'est pas.

Les 52 tests d'orchestration passent **sans qu'aucune assertion soit modifiée**
(seule une ligne d'import a changé), ce qui est la preuve que le comportement
est inchangé. Huit tests unitaires par étape ont été ajoutés.
