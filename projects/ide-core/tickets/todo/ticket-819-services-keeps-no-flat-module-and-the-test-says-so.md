---
id: ticket-819
title: "Services keeps no flat module and the test says so"
type: refactor
status: todo
pr_number: null
priority: low
agent: codeur
depends_on: [ticket-818]
estimated_days: 1
created: 2026-11-05
---

# ticket-819 — `services/` ne garde aucun module à plat, et le test le dit

## Objectif

Le classement de départ devient la règle définitive : plus de table de transition, plus de script de
déplacement, un module à plat ne passe plus.

## Contexte

ADR-074. Les tickets 803 à 818 ont vidé `A_DEPLACER`. Reste la règle sans son échafaudage.

## Ce que le ticket fait

- Déplace `ORDRE` de `scripts/domaines_services.py` dans `backend/tests/test_domaines_services.py`,
  supprime `A_DEPLACER` et le module de données.
- Remplace le test de couverture : tout fichier directement sous `services/`, hors `__init__.py`,
  fait échouer ; chaque dossier de `services/` figure dans `ORDRE`, chaque entrée d'`ORDRE` est un
  dossier.
- Supprime `scripts/deplacer_domaine.py` et son test, et `memory/services-domaines.md` (la liste
  est devenue l'arborescence).
- Vérifie que `contraintes.md` (règle d'ADR-074) dit la même chose que le test, sans la recopier.

## Critères d'acceptation

- [ ] Un fichier posé à plat sous `services/` fait échouer `test_domaines_services.py`
- [ ] `scripts/domaines_services.py`, `scripts/deplacer_domaine.py`, `test_deplacer_domaine.py` et
      `memory/services-domaines.md` n'existent plus
- [ ] `ORDRE` du test porte les dix-huit domaines, dans l'ordre d'ADR-074
- [ ] La suite passe, `ECARTS_DOMAINES` n'a grandi d'aucune ligne

## Ce que ça ne fait pas

Aucun module ne bouge. Les écarts restants de `ECARTS_DOMAINES` se corrigent un à un, hors de ce
ticket, et la liste ne fait que diminuer.
