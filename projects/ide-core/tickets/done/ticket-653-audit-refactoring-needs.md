---
agent: architect
created: 2026-10-28
depends_on:
- ticket-652
estimated_days: 1
id: ticket-653
plan: true
pr_number: null
priority: low
status: done
title: 'Audit: list the refactors the code needs, ranked by cost and risk'
type: design
---

# ticket-653 — Audit des refactos nécessaires

## Objectif
Savoir quels refactos le code demande, à quel coût, et avec quel risque.

## Contexte
Plusieurs fichiers vivent sous un plafond de longueur relevé au fil des tickets
(`frontend/src/longueur-des-fichiers.test.ts`, et l'équivalent backend). Le
28/10, `types/api.ts` a dû être découpé pour accueillir un champ. Un plafond
qui monte signale un fichier qui porte trop.

## Solution proposée
- Lister les fichiers sous plafond, avec leur taille, leur plafond et ce qu'ils
  mélangent.
- Repérer les modules trop couplés : imports circulaires évités par import
  local, fonctions de plus de 80 lignes, classes qui portent plusieurs rôles.
- Classer chaque refacto par coût estimé et par risque de régression, en
  s'appuyant sur les doublons du ticket-652.

## Critères d'acceptation
- [ ] `docs/audit/refactos.md` liste chaque fichier qui a un plafond de longueur, avec sa taille réelle, son plafond et les responsabilités qu'il mélange
- [ ] `docs/audit/refactos.md` classe les refactos proposés par coût et par risque, chacun avec les fichiers qu'il touche
- [ ] Le livrable liste les tickets de refacto, chacun avec ses critères vérifiables

## Ce que ça ne fait pas
- Ne refactore rien : ticket d'audit.