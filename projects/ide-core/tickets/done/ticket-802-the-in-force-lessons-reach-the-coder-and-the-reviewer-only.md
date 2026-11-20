---
agent: codeur
created: 2026-11-05
depends_on: [ticket-801]
estimated_days: 1
id: ticket-802
pr_number: null
priority: medium
status: done
title: The in-force lessons reach the coder and the reviewer only
type: feat
---

# ticket-802 — Les leçons en vigueur n'atteignent que le codeur et le reviewer

## Objectif

Une leçon placée sous `## En vigueur` figure dans le prompt du codeur et du reviewer, sous
les contraintes, et dans celui d'aucun autre rôle (ADR-074).

## Contexte

`build_project_context` (`services/assemblage_run.py`) assemble le contexte commun ; la
section « Décisions récentes » y est réduite par rôle par `adr_pertinents`
(`services/adr.py`). Une section ajoutée après elle passerait à **tous** les rôles : le
filtre par rôle est donc le cœur du ticket. Coût : jusqu'à 4 Ko par appel, dix-huit appels
possibles par ticket (sobriété), d'où deux rôles seulement.

## Ce qu'il faut faire

- `build_project_context` ajoute, après les décisions, `## Leçons du projet` avec une phrase
  d'en-tête (« Pièges observés sur ce projet. Une contrainte ou un ADR qui les contredit
  prévaut. ») puis les leçons `en_vigueur` de `lire_lecons` (ticket-801). Fichier absent ou
  section vide : aucune section, pas de « _Aucune leçon._ ».
- Les leçons `proposees` ne sont jamais lues ici.
- Constante `ROLES_AVEC_LECONS = frozenset({"codeur", "reviewer"})` ; le filtre de rôle
  (dans `adr.py`, à côté de `adr_pertinents`, ou un module voisin si `adr.py` approche
  300 lignes) retire la section pour tout autre rôle, y compris un rôle créé après coup
  (le défaut protège : une leçon ne part qu'à qui est nommé).
- Le contenu lu est borné : au-delà de `PLAFOND_OCTETS`, la lecture tronque aux leçons qui
  tiennent et journalise un avertissement ; elle ne lève pas.

## Critères d'acceptation

- [x] `backend/tests/test_lecons_injection.py` : contexte avec leçons en vigueur → présentes
      pour `codeur` et `reviewer`, absentes pour `securite`, `validateur`, `architect`,
      `doc-technique` et un rôle inconnu
- [x] Une leçon sous `## Proposées` n'apparaît dans le contexte d'aucun rôle
- [x] Fichier absent ou sans leçon en vigueur : le contexte est identique à celui d'avant
      (test d'égalité sur un projet sans `lecons.md`)
- [x] Un fichier de plus de 4 Ko ne produit qu'une section tronquée, sans exception
- [x] Les tests existants de `adr_pertinents` et `build_project_context` passent inchangés

## Ce que ça ne fait pas

Ne produit aucune leçon (ticket-803). Ne touche ni `chat.py` ni les routeurs qui lisent
`lire_contraintes` : le chat n'a pas de leçons.

## Dépendances

ticket-801.
