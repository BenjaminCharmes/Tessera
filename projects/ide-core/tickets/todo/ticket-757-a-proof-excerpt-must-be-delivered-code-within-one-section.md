---
id: ticket-757
title: "A documentation proof excerpt must be delivered code, within one section"
type: fix
status: todo
pr_number: null
priority: low
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-11-03
---

# ticket-757 — Un extrait de preuve doit être du code livré, dans une seule section

## Objectif

La documentation ne peut pas s'appuyer sur du code supprimé ni sur des lignes recollées de
deux endroits.

## Contexte

Audit du 30/10 (relecture du 03/11), ticket-708. `documentation_preuve.py` cherche l'extrait
par sous-chaîne dans le diff brut, lignes `-` comprises ; les lignes livrées de toutes les
sections sont recollées bout à bout, si bien qu'un extrait multi-ligne peut chevaucher deux
sections éloignées. Une ligne ajoutée `++i` (soit `+++i`) est filtrée comme un en-tête.
ADR-057 : une édition cite le code livré qui la fonde.

## Critères d'acceptation

- [ ] Un test vérifie qu'un extrait qui ne figure que sur une ligne `-` est refusé
- [ ] Un test vérifie qu'un extrait de deux lignes tirées de deux sections différentes est
      refusé, et qu'un extrait de deux lignes consécutives d'une même section passe
- [ ] Un test vérifie qu'une ligne ajoutée `++i` sert de preuve
