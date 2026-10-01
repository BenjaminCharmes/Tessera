---
id: ticket-249
title: "Les consignes d'ide-core disent qui tourne et comment s'installer"
type: docs
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-29
---

# ticket-249 — Les consignes d'ide-core disent qui tourne et comment s'installer

## Objectif

Que `projects/ide-core/CLAUDE.md` décrive les agents réellement actifs et le
geste d'installation du hook, et qu'un test empêche la liste de re-diverger.

**Ce ticket autorise explicitement la modification de
`projects/ide-core/CLAUDE.md`** (règle 5 du CLAUDE.md racine).

## Contexte

La section « Agents actifs sur ce projet » nomme 3 rôles ; `agents.json` en
déclare 8 actifs — `doc-technique`, `doc-fonctionnelle` et `project-analyzer`
n'apparaissent nulle part. Rien ne confronte cette section au manifeste dans
`test_consignes_coherentes.py`, c'est l'angle mort qui a laissé passer l'écart.
Par ailleurs `make install-hooks` (deuxième porte d'ADR-050) n'est cité par
aucune consigne : sur un clone neuf, le hook pre-push reste inactif tant que
personne n'y pense. Enfin la ligne sur `pipeline.test_cwd` se lit comme si la
valeur était réglée dans `agents.json`, alors que la clef n'y est pas.

## Solution proposée

Compléter la section « Agents actifs » avec les rôles manquants (une ligne
chacun). Ajouter `make install-hooks` au bloc « Lancement du projet ».
Reformuler la phrase sur `pipeline.test_cwd` (« permettent de », pas « est
réglé à »). Ajouter à `test_consignes_coherentes.py` un test qui extrait les
noms de la section « Agents actifs » et vérifie qu'ils couvrent exactement les
rôles actifs d'`agents.json` (testeur exclu tant que `testeur_enabled` est
faux). Budget du fichier (6 000 caractères) tenu.

## Critères d'acceptation

- [ ] La section « Agents actifs » d'`ide-core/CLAUDE.md` nomme les 8 rôles actifs d'`agents.json`
- [ ] Un test de `test_consignes_coherentes.py` échoue si un rôle actif d'`agents.json` manque à la section, ou l'inverse
- [ ] Le bloc « Lancement du projet » cite `make install-hooks` et son rôle (hook pre-push, ADR-050)
- [ ] La phrase sur `pipeline.test_cwd` ne laisse plus croire que la clef est présente dans `agents.json`
- [ ] `ide-core/CLAUDE.md` reste sous son budget de 6 000 caractères

## Dépendances

Aucune.

## Estimation

0.5 jour.

## Risques

Le test de correspondance doit tolérer la mise en forme (gras, tirets) pour ne
pas devenir un test de ponctuation.
