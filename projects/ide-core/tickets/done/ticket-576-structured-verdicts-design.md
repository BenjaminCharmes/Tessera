---
agent: architect
created: 2026-10-24
depends_on:
- ticket-574
estimated_days: 1
id: ticket-576
plan: true
pr_number: 700
priority: low
status: done
title: Design of structured verdicts for reviewer, security and validator
type: design
---

# ticket-576 — Conception de verdicts structurés

## Objectif
Décider si le reviewer, l'audit de sécurité et le validateur rendent leur
verdict en JSON validé par un schéma, au lieu d'un texte lu par mot-clé.

## Contexte
Veille du 24/10 : le SDK épinglé accepte `output_format` avec un schéma JSON.
Aujourd'hui, `_parse_reviewer_verdict` (`services/pipeline_text.py`) lit le
verdict par mot-clé (ADR-009), et une réponse illisible fait refuser (règle
d'échec fermé, ADR-039). Le validateur tourne sur Ollama, avec repli sur Haiku :
le schéma doit avoir un équivalent côté Ollama (paramètre `format`).

## À trancher par la conception
- Le schéma de chaque rôle (verdict, remarques, sévérité, confiance du
  ticket-574).
- Ce que devient le parseur par mot-clé : repli, ou retrait.
- L'équivalent pour le provider Ollama, et pour le repli.
- Ce qui se passe sur un JSON invalide (échec fermé, comme aujourd'hui).

## Critères d'acceptation
- [ ] Une ADR au prochain numéro libre de `memory/decisions.md` décrit le format retenu et ce qu'il remplace, ou pourquoi il est écarté
- [ ] Le livrable liste les tickets d'implémentation qui en découlent, chacun avec ses critères vérifiables

## Ce que ça ne fait pas
- N'implémente rien : ticket de conception.