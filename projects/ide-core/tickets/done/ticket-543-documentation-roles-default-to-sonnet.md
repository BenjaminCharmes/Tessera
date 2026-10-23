---
agent: codeur
created: 2026-10-23
depends_on: []
id: ticket-543
pr_number: 611
priority: medium
status: done
title: Documentation roles default to Sonnet
type: chore
---

## Objectif

Que `doc-technique` et `doc-fonctionnelle` reçoivent par défaut le modèle de
production, quand le manifeste d'un projet n'en déclare pas (ADR-057).

## Critères d'acceptation

- [ ] `modele_par_defaut("doc-technique")` et `modele_par_defaut("doc-fonctionnelle")` rendent `MODELE_PRODUCTION` ; les autres rôles de jugement (sécurité, validateur, et le reste) gardent `MODELE_JUGEMENT`
- [ ] Le repli `_MODELE` de `services/documentation.py` suit, sans dupliquer la constante
- [ ] Le manifeste écrit pour un projet nouveau déclare ce modèle pour les deux rôles
- [ ] Les tests de `modeles_par_defaut` (ticket-397) sont adaptés et un test nomme les deux rôles
- [ ] La docstring du module `modeles_par_defaut.py` ne dit plus « documentation sur Haiku »
- [ ] Aucun `agents.json` existant n'est modifié par ce ticket

## Ce que ça ne fait pas

- Ne touche pas aux `agents.json` des projets : un agent ne les écrit pas. Kadoomi, Devinoo et les autres déclarent encore Haiku jusqu'à ce que Benjamin les change.