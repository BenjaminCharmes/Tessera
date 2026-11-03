---
agent: codeur
created: 2026-10-28
depends_on: []
estimated_days: 1
id: ticket-625
pr_number: 736
priority: medium
status: done
title: The break room keeps a pull request waiting for CI after the queue has moved
  on
type: fix
---

# ticket-625 — La salle de pause suit les PR en CI après le ticket courant

## Objectif
Qu'une PR dont la CI tourne se voie en salle de pause, même quand la file est
passée au ticket suivant.

## Contexte
`laPause` (`lib/bureau/salles.ts`) lit l'état de la boîte aux lettres, et
`boiteAuxLettres` (`lib/bureau/boiteAuxLettres.ts`) ne lit que `etat.ticketEvents`,
c'est-à-dire le ticket courant. Dans une file, la phase 2 (CI puis merge) part
dans `CIWatcher` et le ticket suivant démarre aussitôt (ADR-051). Sa PR
disparaît donc du Bureau avant que sa CI ait rendu. Le 28/10, des PR ont été
mergées sans qu'aucun agent ne passe en salle de pause.

## Solution proposée
Lire, dans `etat.events` (toute la file), les `livraison_done` confiés au
watcher (même règle que `surveilleeParLeWatcher`) qu'aucun `ci_merge_done`
portant le même `pr_number` n'a suivis. Chacun tient le projet en salle de pause
avec « CI en cours de la PR #N ». La boîte aux lettres de la pièce reste celle
du ticket courant.

## Critères d'acceptation
- [ ] Un test de `lib/bureau/salles.ts` vérifie qu'un `livraison_done` confié au watcher, suivi d'un `queue_progress` vers le ticket suivant et sans `ci_merge_done`, met le projet en salle de pause avec « CI en cours de la PR #N »
- [ ] Un test vérifie qu'un `ci_merge_done` portant le même `pr_number` retire la PR de la salle de pause
- [ ] Un test vérifie qu'un `livraison_done` porteur d'un `arret`, et sans `pr_orpheline`, n'amène personne en salle de pause
- [ ] Un test vérifie que `boiteAuxLettres` continue de ne lire que `etat.ticketEvents`

## Ce que ça ne fait pas
- N'ajoute aucun événement backend : ceux de la file suffisent.