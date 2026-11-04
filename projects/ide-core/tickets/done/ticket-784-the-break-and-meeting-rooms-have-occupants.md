---
id: ticket-784
title: "The break and meeting rooms have occupants, drawn from what the run waits for"
type: feat
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-11-04
---

# ticket-784 — Les salles de pause et de réunion ont des occupants

## Objectif

Les salles de pause et de réunion montrent qui y est, au lieu d'une seule ligne de texte en
haut à droite.

## Contexte

Benjamin, le 04/11 : « je n'ai jamais vu personne dans la salle de réunion et dans la salle de
pause ». La salle de pause n'écrivait qu'une ligne (« CI en cours de la PR #… ») pendant les
quelques minutes de CI de chaque ticket, sans personnage ; la salle de réunion ne dessinait le
résolveur que pendant les secondes d'une résolution de conflit. Vérifié : la détection de la CI
fonctionne, y compris quand la file est déjà passée au ticket suivant.

## Solution

Faite à la main. Chaque occupant vient d'un état du run (ADR-058).
- Pause, CI en cours : le validateur qui a approuvé la livraison, la PR en main.
- Pause, quota épuisé : le codeur et le reviewer, tasse en main.
- Pause, dépendance attendue : le codeur, tasse en main.
- Réunion, conflit en cours : le reviewer rejoint le résolveur.
- Réunion, PR de conflit à relire : le résolveur reste, la PR en main.
Chaque personnage a son nom et le motif au survol.

## Critères d'acceptation

- [x] `SallesCommunes.test.tsx` vérifie le validateur pendant la CI (même file passée au ticket
      suivant) et son départ au `ci_merge_done`
- [x] `SallesCommunes.test.tsx` vérifie le codeur et le reviewer sur quota épuisé, le codeur sur
      une dépendance attendue
- [x] `SallesCommunes.test.tsx` et `Salles.test.tsx` vérifient le reviewer pendant un conflit et
      le résolveur, PR en main, pendant la relecture
