---
id: ticket-1057
title: "Run the coder bench pilot on three entries"
type: chore
status: in-progress
priority: medium
agent: codeur
depends_on: [ticket-1055, ticket-1056]
estimated_days: 1
created: 2026-11-26
---

# ticket-1057 — Pilote du banc du codeur sur trois entrées

## Objectif

Mesurer le coût et la durée réels d'une cellule, et vérifier que le rejeu marche, avant de figer le corpus.

## Contexte

Conception §7. Trois entrées `pilote` (hors gel) × trois bras, plafond 15 $. Le pilote ne compte pour aucune
décision. Lancer l'essai consomme du quota d'abonnement : relever le quota avant.

## Solution proposée

Lancer `scripts/banc_codeur.py --pilote --budget-usd 15`, puis écrire `docs/essais/banc-codeur/pilote.md`.

## Critères d'acceptation

- [ ] Trois entrées `pilote` figurent dans `corpus.json`, hors de `gel_sha256`, et n'appartiennent pas aux 20 de l'essai.
- [ ] Les neuf cellules sont consignées dans un `resultats-pilote.jsonl` distinct, sans dépasser 15 $.
- [ ] `pilote.md` donne le coût moyen par cellule, par bras, et le coût projeté pour 65 cellules.
- [ ] `pilote.md` dit pour chaque cellule si la copie s'installe, si les tests tournent et si la référence (`sha`)
      est verte ; une entrée en `echec_env` est remplacée.
- [ ] `pilote.md` propose la taille du corpus (16 à 20) tenant sous le plafond de 100 $, avec son calcul.
- [ ] Le diff ne contient ni `backend/src/`, ni `agents.json`, ni `agents/prompts/`.

## Ce que ça ne fait pas

- Ne conclut rien sur les bras ; ne fige pas le corpus de l'essai.

## Dépendances

ticket-1055, ticket-1056.

## Estimation

Une journée, dont l'essentiel en attente de tests.

## Risques

Un pilote de neuf cellules qui coûte plus de 15 $ se coupe : le plafond est la règle, pas une indication.
