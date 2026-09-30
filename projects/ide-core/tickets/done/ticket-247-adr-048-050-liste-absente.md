---
id: ticket-247
title: "ADR-048 et ADR-050 disent la même chose sur la liste absente"
type: docs
status: done
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-29
---

# ticket-247 — ADR-048 et ADR-050 disent la même chose sur la liste absente

## Objectif

Que les deux ADR sur les termes interdits décrivent le comportement réel du
code quand `FORBIDDEN_TERMS` est absente, sans se contredire.

## Contexte

ADR-048 dit « Liste vide ou absente : aucun contrôle ». ADR-050 dit « Liste
absente ou git en échec : refus ». Le code suit ADR-048 sur les deux portes
locales — le hook `pre-push` fait `return 0` sans termes, le backend saute le
contrôle (`termes_interdits.py:126`, `github_workflow.py:214`) — et ADR-050
seulement en CI (`termes_interdits_ci.py:39`). Par ailleurs le job CI
s'intitule « Termes interdits (ADR-048) » alors qu'il met en œuvre ADR-050.

## Solution proposée

Entériner le comportement du code, qui est le bon : en local, une liste
absente signifie que le contrôle n'est pas configuré sur cette machine — un
clone neuf doit pouvoir pousser ; en CI, le secret est déclaré côté dépôt,
son absence est une panne de configuration et refuse. Un échec git refuse
partout. Amender ADR-050 (mention « amendé 2026-09-29 » dans le texte, budget
de 160 mots tenu) et renommer le job CI.

## Critères d'acceptation

- [ ] ADR-050 distingue liste absente en local (aucun contrôle, renvoi vers ADR-048) et en CI (refus)
- [ ] ADR-050 garde « git en échec : refus » pour toutes les portes
- [ ] ADR-048 et ADR-050 ne portent plus deux phrases contradictoires sur la liste absente
- [ ] Le job de `.github/workflows/ci.yml` cite ADR-050, plus ADR-048
- [ ] ADR-050 amendé tient sous les 160 mots mesurés par `test_consignes_coherentes.py`

## Dépendances

Aucune.

## Estimation

0.5 jour.

## Risques

Aucun changement de code : le comportement documenté est celui qui tourne.
