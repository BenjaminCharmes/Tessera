---
id: ticket-729
title: "Server rooms show only the product's agents"
type: fix
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: [ticket-712]
estimated_days: 1
created: 2026-11-02
---

# ticket-729 — Les salles serveur ne montrent que les agents du produit

## Objectif

Qu'une salle de « En cours » ne dessine que les agents **du produit** (le tour de la
semaine de Vigie, la recherche de prix d'Affût), jamais ceux du pipeline Tessera.

## Contexte

Le ticket-712 a posé dans la salle d'un projet un poste pour l'agent du pipeline qui
traite un ticket. Benjamin, le 02/11 : « Les agents qui s'occupent des tickets sont déjà
dans les Bureaux. » Le poste faisait doublon et brouillait ce que la salle doit dire.

## Solution proposée

- Retirer le poste du pipeline (`PosteDeFile`) de la salle ; garder le badge bleu de la
  plaque (« File 3/6 · ticket-059 »), qui signale seulement qu'une file travaille ici.
- Au passage : ticket-728 passe en `done/` ; `dependabot.yml` ignore mypy ≥ 1.19
  (Smart App Control, ticket-385 ; #812 fermée).

## Critères d'acceptation

- [x] Un test de `SallesDesServeurs.test.tsx` vérifie qu'avec un run ouvert la salle
      porte le badge et aucun poste ni agent du pipeline
- [x] `PosteDeFile.tsx` est supprimé ; `BadgeDeFile.tsx` porte le badge
- [x] `.github/dependabot.yml` ignore `mypy` aux versions `>=1.19`

## Dépendances

ticket-712.

## Estimation

Une heure.

## Risques

Aucun : un retrait.
