---
id: ticket-700
title: "Delivery phase one in named steps"
type: refactor
status: todo
priority: low
agent: codeur
depends_on: [ticket-677]
created: 2026-10-29
---

# ticket-700 — `livrer_phase_1` en étapes nommées

## Objectif
La première phase de livraison (rebase, push, PR) se lit comme une suite
d'étapes, chacune testable seule.

## Contexte
`services/livraison.py:122-284` : `livrer_phase_1` fait ≈ 163 lignes, la plus
longue fonction de livraison, et `livrer_phase_2` (372-459) ≈ 88.
Elle porte les portes de livraison (ADR-029, ADR-030, ADR-033, ADR-039).
Le ticket-677 remplace d'abord l'exécuteur git qu'elle appelle.
`docs/audit/refactos.md` §2.2.

## Critères d'acceptation
- [ ] Chaque étape (contrôle d'approbation, rebase, push, ouverture de PR) est une méthode ou une fonction nommée ; la PR cite la longueur de chacune, mesurée par un `ast` jetable non commité, aucune au-dessus de 80 lignes
- [ ] L'ordre des portes et leurs messages d'arrêt (`Livraison.arret`) sont inchangés : les tests existants de `livrer_phase_1` passent sans changement de leurs attendus
- [ ] Un run non approuvé ne se livre toujours pas et une approbation vaut toujours pour `approved_sha` (ADR-030, ADR-039) : un test existant ou neuf le couvre, cité dans la PR
- [ ] L'entrée de `services/livraison.py` dans `PLAFONDS` est baissée si le fichier rétrécit (le cliquet l'exige)
- [ ] `uv run pytest` et `uv run mypy` passent

## Ce que ça ne fait pas
- Ne change aucune condition de livraison, de rebase ni de merge
- Ne touche pas à `CIWatcher` ni à la phase 2
