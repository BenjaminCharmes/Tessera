---
id: ticket-598
title: "The room celebrates a merged PR, and a beacon turns while the CI is red"
type: feat
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: ["ticket-596"]
estimated_days: 0.5
created: 2026-10-27
---

# ticket-598 — Fête au merge, gyrophare sur CI rouge

## Objectif
Idée 1 du « Bureau vivant » (`design/maquette/Bureau-vivant.dc.html`, boutons
de démo « PR mergée » et « CI rouge »), validée par Benjamin le 27/10.

## Contexte
L'issue de la phase 2 arrive par `ci_merge_done` (`data.merged`, `data.arret`)
et se lit déjà dans `lib/bureau/boiteAuxLettres.ts` (états `mergee` et
`refusee`).

## Ce que dit la maquette
- **PR mergée** : pendant 10 s après un `ci_merge_done` avec `merged: true`,
  les agents de la pièce se lèvent bras levés devant leur poste, des confettis
  tombent (18 carrés de 4 × 6 px, cinq couleurs), le contour passe au vert et
  la pastille dit « PR mergée ».
- **CI rouge** : tant que la boîte est `refusee` (CI rouge ou merge refusé),
  un gyrophare rouge clignote au plafond de la pièce et son contour passe au
  rouge. Il s'éteint au `livraison_started` suivant ou au rangement du run.
- `prefers-reduced-motion` : pas de chute de confettis ni de clignotement ;
  les états restent visibles (contours, pastille, gyrophare allumé fixe).

## Critères d'acceptation
- [ ] Après un `ci_merge_done` `merged: true`, la pièce rend des éléments `data-sprite="confetti"` et les agents en pose « bras levés » ; un test le vérifie
- [ ] 10 s plus tard (temps simulé), il n'y a plus de confettis ; un test le vérifie
- [ ] Après un `ci_merge_done` `merged: false`, la pièce rend un `data-sprite="gyrophare"` ; un test le vérifie
- [ ] Après un `livraison_started` suivant, le gyrophare disparaît ; un test le vérifie
- [ ] Sous `prefers-reduced-motion: reduce`, les animations `chute` et `gyro` sont coupées ; un test de source le vérifie
- [ ] Le diff ne modifie aucun fichier de `backend/`
