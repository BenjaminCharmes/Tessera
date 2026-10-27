---
agent: codeur
created: 2026-10-26
depends_on: []
estimated_days: 0.5
id: ticket-584
pr_number: null
priority: high
status: done
title: The post-rebase retest runs only when the base brought changes to a chain the
  branch also touches
type: chore
---

# ticket-584 — Retester après rebase seulement si la base touche la même chaîne

## Objectif
Ne plus repasser dix minutes de tests à la livraison quand ce que la base a
apporté ne peut pas casser ce que la branche touche.

## Contexte
Le ticket-568 relance les tests à la livraison dès que la base a avancé
(`backend/src/tessera/services/retest_apres_rebase.py`, `base_a_avance`).
Le 26/10, le ticket-579 (diff dans `backend/`) a retesté pytest et mypy
pendant ~10 min après un testeur vert de 9 min 24 s, parce que develop avait
reçu le 567 et la PR #649 — du frontend et des tickets, rien sous `backend/` ni
`scripts/`. Pendant ce temps le projet garde son verrou, et le ticket suivant
attend.

`scripts/verifier.py` découpe déjà le dépôt en chaînes : `backend/` et
`scripts/` → pytest et mypy ; `frontend/` → tsc, eslint, vitest ; le reste →
rien. La CI GitHub rejoue tout à chaque PR et reste la porte complète.

## Solution proposée
Avant le rebase, comparer les chemins que la base apporte
(`git diff --name-only HEAD...<base>`) aux chemins de la branche
(`git diff --name-only <base>...HEAD`) : retester seulement si une chaîne du
verifier est touchée des deux côtés. Les préfixes des chaînes sont lus dans
un seul endroit côté backend, et un test les confronte à `scripts/verifier.py`
(qui reste protégé, ADR-027 : on le lit, on ne le modifie pas).
Échoue fermé (ADR-039) : une liste de chemins illisible → retest, comme
aujourd'hui. Un projet sans `scripts/verifier.py` garde le comportement
actuel (la base a avancé → retest).

## Critères d'acceptation
- [ ] Base qui n'apporte que des fichiers `frontend/` et branche qui ne touche que `backend/` : pas de retest ; un test le vérifie
- [ ] Base et branche qui touchent toutes deux `backend/` (ou `scripts/` et `backend/`) : retest ; un test le vérifie
- [ ] Liste de chemins illisible (git qui lève ou renvoie `None`) : retest ; un test le vérifie
- [ ] Un projet dont le `test_cwd` n'a pas de `scripts/verifier.py` retest dès que la base a avancé, comme avant ; un test le vérifie
- [ ] Un test vérifie que les préfixes de chaînes du backend sont ceux de `scripts/verifier.py`
- [ ] Le diff ne modifie pas `scripts/verifier.py`