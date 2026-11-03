---
agent: architect
created: 2026-10-29
depends_on: []
estimated_days: 1
id: ticket-668
plan: true
pr_number: 765
priority: medium
status: done
title: 'Design: split a run into sub-tasks implemented, reviewed and committed one
  by one'
type: design
---

# ticket-668 — Conception : des sous-tâches dans un run

## Objectif
Décider si un run découpe son ticket en sous-tâches, chacune implémentée, relue et
commitée à son tour, avec les tests globaux une seule fois après la dernière.

## Contexte
Piste reçue le 29/10 d'une session tierce, tirée d'un IDE comparable. Aujourd'hui,
un run fait un seul diff par tour, que testeur, sécurité, reviewer et validateur
jugent en bloc. Un ticket coûte environ 45 minutes, dont 27 de tests
(`memory/tests-locaux-cibles-ci-complete`). Un refus renvoie tout le diff au codeur,
et un gros ticket épuise les actions du codeur (`LLM_MAX_TURNS`).

Contraintes en vigueur : une branche et un commit par run (ADR-018) ; verdicts
structurés (ADR-061) ; plan préalable optionnel (`plan: true`, ticket-243).

## Solution proposée
- Comparer trois formes : sous-tâches tirées du plan (`plan: true`), sous-tâches
  écrites dans le ticket, ou statu quo avec des tickets plus petits.
- Pour chaque forme : effet sur le coût en tokens et en minutes, sur ADR-018 (un
  commit par sous-tâche ou un seul à la fin), sur ce que voient reviewer et
  validateur, et sur la reprise d'un run interrompu.
- Recommander d'adopter, de réduire ou d'écarter.

## Critères d'acceptation
- [ ] Une ADR au prochain numéro libre de `memory/decisions.md` décrit la forme retenue, ou pourquoi l'idée est écartée
- [ ] Le livrable chiffre, pour chaque forme, l'effet attendu sur la durée et le coût d'un ticket, en partant des durées réelles de `memory/pipeline-log.md`
- [ ] Le livrable liste les tickets d'implémentation qui en découlent, chacun avec ses critères vérifiables

## Ce que ça ne fait pas
- N'implémente rien : ticket de conception.