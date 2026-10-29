---
agent: architect
created: 2026-10-28
depends_on:
- ticket-650
estimated_days: 1
id: ticket-651
plan: true
pr_number: 761
priority: medium
status: done
title: 'Audit: check the code against the constraints in force and the house rules'
type: design
---

# ticket-651 — Audit du respect des règles

## Objectif
Vérifier que le code respecte les contraintes en vigueur et les règles de la
maison, et lister les écarts.

## Contexte
Plus de cinq cents tickets ont été livrés. Les règles vivent dans
`memory/contraintes.md` (par rôle), dans `CLAUDE.md` (conventions de code) et
dans les tests de cohérence (`test_consignes_coherentes.py`, plafonds de
longueur, couleurs d'ADR-026). Une règle sans test peut avoir dérivé sans
que personne ne le voie.

## Solution proposée
- Pour chaque règle de `contraintes.md` en vigueur (statuts du ticket-650) :
  dire si un test la garde, et chercher dans le code un écart.
- Contrôler les conventions de `CLAUDE.md` : langue des identifiants et des
  commentaires (ADR-044), `any` en TypeScript, `console.log`, fichiers de plus
  de 200 lignes sans plafond déclaré, fonctions publiques sans test.

## Critères d'acceptation
- [ ] `docs/audit/regles.md` liste chaque règle en vigueur de `contraintes.md`, le test qui la garde (fichier et nom) ou « aucun test »
- [ ] `docs/audit/regles.md` liste chaque écart trouvé avec son `fichier:ligne`
- [ ] Le livrable liste les tickets de correction, chacun avec ses critères vérifiables, en commençant par les règles sans test

## Ce que ça ne fait pas
- Ne corrige rien : ticket d'audit.