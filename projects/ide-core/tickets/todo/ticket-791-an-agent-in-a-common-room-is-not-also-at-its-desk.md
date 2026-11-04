---
id: ticket-791
title: "An agent in the break or meeting room is not also drawn at its desk"
type: fix
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-11-04
---

# ticket-791 — Un agent en salle de pause ou de réunion n'est pas aussi dessiné à son bureau

## Objectif

Dans le Bureau, chaque agent d'un projet n'apparaît qu'à un seul endroit à la fois.

## Contexte

Benjamin, le 04/11 : le validateur d'ide-core est en salle de pause pendant la CI d'une PR, et il
est aussi assis à son bureau dans la salle du projet. Il apparaît donc en double.

Le ticket-784 a placé des occupants dans les salles communes (`SallePause.tsx`, table
`OCCUPANTS` : le validateur pendant la CI, le codeur et le reviewer sur un quota épuisé, le codeur
sur une dépendance attendue ; `SalleReunion.tsx` : le reviewer pendant un conflit). La salle du
projet n'en sait rien : `Piece.tsx` ne retire de son bureau que les agents de `postesAbsents`
(`frontend/src/lib/bureau/sallesCommunes.ts`), c'est-à-dire ceux qui sont chez le directeur ou
aux RH.

Une mascotte par projet a été écartée : elle ne rendrait aucune donnée (ADR-058).

## Solution proposée

- Sortir la table `OCCUPANTS` de `SallePause.tsx` vers `frontend/src/lib/bureau/salles.ts`, avec
  une fonction qui rend, pour l'état d'un run, les postes en pause et ceux en réunion. Les deux
  salles communes et la salle du projet lisent cette même fonction.
- Un poste « occupé » dans le run courant (`postesDuRun`, le ticket suivant de la file est déjà
  au travail) reste à son bureau : il n'est pas compté en pause, et la salle de pause ne le
  dessine pas. La ligne de texte de la salle (« CI en cours de la PR #… ») reste affichée.
- `postesAbsents` ajoute les postes en pause et en réunion à ceux du directeur et des RH. Le
  bureau d'un absent s'affiche comme celui d'un agent parti chez le directeur.

## Critères d'acceptation

- [ ] Un test de `salles.test.ts` vérifie que, pendant la CI d'une PR, le validateur est en pause
      quand il n'est pas occupé par le run courant, et ne l'est pas quand il est occupé
- [ ] Un test de `sallesCommunes.test.ts` vérifie que `postesAbsents` contient le validateur
      pendant la CI, et le reviewer pendant un conflit en salle de réunion
- [ ] Un test de `Piece` vérifie que, pendant la CI d'une PR, le poste du validateur porte
      `data-absent="true"` (comme un agent parti chez le directeur, `PosteDeTravail.tsx`) quand
      le validateur n'est pas occupé par le run courant
- [ ] Un test de `SallePause` vérifie qu'un validateur occupé par le run courant n'est pas dessiné
      en salle de pause, et que la ligne « CI en cours » reste visible
