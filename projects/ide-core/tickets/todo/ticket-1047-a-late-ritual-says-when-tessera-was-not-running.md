---
id: ticket-1047
title: "Un rituel en retard dit combien et pendant quelle interruption il est tombé"
type: feat
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: ["ticket-1046"]
estimated_days: 1
created: 2026-11-23
---

# ticket-1047 — Un retard qui s'explique

## Objectif
Que le bandeau et la carte d'un rituel en retard disent « en retard de X h »
et, si une interruption couvre l'échéance, « Tessera n'a pas tourné du … au … ».

## Contexte
Le bandeau signale déjà `en_retard`, sans durée ni cause. Les périodes
d'interruption viennent de `GET /api/v1/rituels/interruptions` (ticket-1046).
Le rattrapage n'a pas besoin d'un nouveau mécanisme : l'échéance dépassée reste
en retard jusqu'à « fait » ou « reporté ».

## Solution proposée
Frontend seul : `useRituels` charge aussi les interruptions ; `CarteRituel`
affiche le retard (depuis `derniere`) et l'interruption qui contient `derniere`,
en heure locale. Pas de couleur nouvelle hors des teintes d'état (ADR-026).

## Critères d'acceptation
- [ ] Un test de `RituelsView.test.tsx` vérifie qu'un rituel en retard depuis 9 h 12 min affiche « en retard de 9 h ».
- [ ] Un test vérifie qu'une interruption contenant l'échéance ajoute « Tessera n'a pas tourné du » suivi des deux heures.
- [ ] Un test vérifie qu'un rituel en retard sans interruption n'affiche pas cette phrase.
- [ ] `apiRituels.ts` appelle `/api/v1/rituels/interruptions` avec le jeton, et un échec de cet appel laisse la liste des rituels s'afficher.
- [ ] `npm run lint` et `tsc` passent sans erreur sur les fichiers modifiés.

## Dépendances
ticket-1046.

## Estimation
Un jour.

## Risques
Une durée en minutes est arrondie à l'heure sous une journée, au jour au-delà :
le texte ne promet pas plus de précision que l'échéance n'en a.
