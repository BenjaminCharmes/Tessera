---
agent: codeur
created: 2026-11-23
depends_on:
- ticket-1046
estimated_days: 1
id: ticket-1047
pr_number: 1259
priority: medium
status: done
title: Un rituel en retard dit combien et pendant quelle interruption il est tombé
type: feat
---

# ticket-1047 — Un retard qui s'explique

## Objectif
Que la carte d'un rituel en retard (`CarteRituel`, écran Rituels) dise
« en retard de X h » et, si une interruption couvre l'échéance, « Tessera n'a
pas tourné du … au … ».

## Contexte
La carte d'un rituel en retard dit aujourd'hui « Depuis <date> », sans durée
ni cause ; la pastille et la cloche ne donnent qu'un nombre. Il n'y a pas de
bandeau des rituels, et il n'en faut pas : Benjamin l'a refusé au ticket-903.
Les périodes d'interruption viennent de `GET /api/v1/rituels/interruptions`
(ticket-1046) : `{"interruptions": [{"debut", "fin"}]}`, heures locales sans
fuseau, comme `derniere`.
Le rattrapage n'a pas besoin d'un nouveau mécanisme : l'échéance dépassée reste
en retard jusqu'à « fait » ou « reporté ».

## Solution proposée
Frontend seul : `lireInterruptions()` dans `apiRituels.ts` (par `request`,
qui porte le jeton) ; `useRituels` les charge à côté des rituels, dans un
`try` séparé, et les expose dans `UseRituelsResult` ; `CarteRituel` affiche le
retard (depuis `derniere`) et l'interruption qui contient `derniere`, en heure
locale. Pas de couleur nouvelle hors des teintes d'état (ADR-026), pas de
bandeau. `GET /api/v1/rituels/interruptions` reste dans `HORS_PERIMETRE`
(ticket-1046), comme `GET /api/v1/rituels`.

## Critères d'acceptation
- [ ] Un test de `RituelsView.test.tsx`, à heure fixée (`vi.setSystemTime`), vérifie qu'un rituel en retard depuis 9 h 12 min affiche « en retard de 9 h ».
- [ ] Un test vérifie qu'une interruption contenant l'échéance ajoute « Tessera n'a pas tourné du » suivi des deux heures.
- [ ] Un test vérifie qu'un rituel en retard sans interruption n'affiche pas cette phrase.
- [ ] `apiRituels.ts` exporte `lireInterruptions`, qui lit `/rituels/interruptions` par `request`.
- [ ] Un test de `useRituels` (nouveau fichier `frontend/src/hooks/useRituels.test.ts`) montre qu'un échec de `lireInterruptions` laisse les rituels lus et rend une liste d'interruptions vide.
- [ ] `npm run lint` et `tsc` passent sans erreur sur les fichiers modifiés.

## Dépendances
ticket-1046.

## Estimation
Un jour.

## Risques
Une durée en minutes est arrondie à l'heure sous une journée, au jour au-delà,
et dite en minutes sous une heure (jamais « en retard de 0 h ») :
le texte ne promet pas plus de précision que l'échéance n'en a.