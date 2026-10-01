---
agent: codeur
created: 2026-10-01
depends_on: []
estimated_days: 0.5
id: ticket-287
pr_number: null
priority: medium
status: done
title: Clicking the board toggle from the run view opens the board
type: fix
---

# ticket-287 — « Vue tableau » depuis le run ouvre le tableau

## Objectif

Qu'un clic sur « Vue tableau » ouvre le tableau quand le centre affiche le
run, au lieu de tomber sur « Aucun fichier ouvert ».

## Contexte

Retour d'usage du 2026-10-01 : depuis la vue du run en cours, cliquer sur
« Vue tableau » affiche l'éditeur vide, et le bouton se désélectionne. Il faut
cliquer une seconde fois.

`onToggleKanban` (`hooks/useCockpit.ts:313-320`) fait
`setShowKanban((v) => !v)`, c'est-à-dire qu'il inverse l'état mémorisé, et
non ce qui est affiché. Quand le run occupe le centre (`vueDuCentre.ts:34`),
`showKanban` vaut souvent déjà `true`, puisque le tableau était le choix
« sous » le run. Le clic le passe à `false`, et `vueDuCentre` rend l'éditeur.

## Solution proposée

`onToggleKanban` décide depuis la vue affichée : si le centre montre le
tableau, il passe à l'éditeur ; sinon (run, éditeur, fichier, diff), il
ouvre le tableau. L'état actif du bouton se lit lui aussi depuis la vue
affichée, pas depuis `showKanban`.

## Critères d'acceptation

- [ ] Un test de `useCockpit` vérifie qu'avec un run au premier plan et
      `showKanban` à `true`, un appel à `onToggleKanban` donne la vue
      `kanban`
- [ ] Un test vérifie que, depuis le tableau affiché, `onToggleKanban` donne
      la vue `editor`
- [ ] Un test vérifie que le bouton « Vue tableau » n'apparaît pas actif tant
      que le centre affiche le run

## Dépendances

Aucune. Le ticket-283 touche aussi la navigation de `useCockpit`. S'il est
mergé avant, celui-ci se rebase dessus.

## Estimation

0,5 jour.

## Risques

Aucun.