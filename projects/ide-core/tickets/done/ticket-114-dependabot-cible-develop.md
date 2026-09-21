---
id: ticket-114
title: "Dependabot ouvre ses PR vers develop, comme tout le monde"
type: fix
status: done
pr_number: 130
priority: medium
agent: codeur
depends_on: ["ticket-108"]
estimated_days: 1
created: 2026-09-21
---

# ticket-114 — Dependabot ouvre ses PR vers develop, comme tout le monde

## Objectif

Que les mises à jour de dépendances suivent le même flux que le reste.

## Contexte

Les sept PR ouvertes par Dependabot ciblent **`main`**. Le flux du dépôt veut
l'inverse : toutes les PR vont vers `develop`, et rien n'entre dans `main`
autrement que par une PR de release.

La cause est une omission du ticket-108, qui a configuré Dependabot sans
déclarer `target-branch`. Sans cette clef, Dependabot vise la branche **par
défaut** du dépôt — `main` — et ses PR arrivent donc à contre-courant.

Deux conséquences. Une mise à jour mergée sauterait `develop`, qui est le seul
endroit où les changements sont testés **fusionnés entre eux** ; et `main` et
`develop` divergeraient aussitôt, chaque release suivante rejouant le conflit.

## Solution proposée

1. Déclarer `target-branch: "develop"` sur les quatre écosystèmes.
2. **Retarger** les sept PR existantes plutôt que les fermer : le skill
   `ticket-workflow` le dit — une PR ouverte vers `main` se retarge, on ne la
   rouvre pas. Fermer perdrait aussi les rebases déjà faits.

## Critères d'acceptation

- [x] Les quatre écosystèmes de `.github/dependabot.yml` déclarent
      `target-branch: "develop"`
- [x] Les sept PR ouvertes ciblent `develop`
- [x] `.\scripts\tessera.ps1 verify` est vert de bout en bout

## Ce que ça ne fait pas

Ne merge aucune mise à jour. Quatre des sept sautent trois versions majeures
d'actions qui font tourner la CI elle-même : elles se relisent une par une, et
c'est leur propre CI qui tranche.

## Dépendances

ticket-108, qui a introduit l'omission.

## Estimation

1 jour.

## Risques

Aucun sur le dépôt : la clef ne change que la cible des PR à venir. Les PR
retargées repartent de `develop`, donc leur CI rejoue sur la bonne base — ce
qui est précisément ce qu'on veut vérifier avant de merger quoi que ce soit.
