---
id: ticket-961
title: "Rituals follow the three monthly work deadlines"
type: chore
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 0.1
created: 2026-11-13
---

# ticket-961 — Les rituels suivent les trois échéances mensuelles du travail

## Objectif
Que l'onglet Rituels rappelle à temps les trois échéances mensuelles que
Benjamin a précisées le 13/11 : pointage horaire et rapport d'activité au plus
tard le 20, note de frais au plus tard le 27.

## Contexte
`rituels.md` portait un seul rappel mensuel, le 18 avec une limite au 22 : la
limite réelle est le 20, le pointage n'était pas nommé et la note de frais
n'avait aucun rappel. Retouche faite à la main (petite retouche, sans pipeline).

## Solution proposée
- `rapport-mensuel` : le 15 à 10 h, `avant: 20`, titre et détail qui nomment le
  pointage ; l'id ne change pas, l'état « fait » s'y rattache.
- Nouveau rituel `note-de-frais` : le 22 à 10 h, `avant: 27`, sans projet.
- Libellés génériques, aucun nom d'employeur ni d'outil.

## Critères d'acceptation
- [x] `rituels.md` donne à `rapport-mensuel` le rythme mensuel `jour: 15`, `avant: 20`
- [x] `rituels.md` déclare `note-de-frais`, mensuel, `jour: 22`, `avant: 27`
- [x] `lire_definitions` lit le fichier sans erreur

## Ce que ça ne fait pas
- Le pointage et le rapport restent un seul rappel : même date limite, même moment.
