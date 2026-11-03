---
id: ticket-720
title: "Bureau agents do not slide when the floor changes width"
type: fix
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 0.1
created: 2026-10-30
---

# ticket-720 — Les agents du Bureau ne glissent plus quand le sol change de largeur

## Objectif
En revenant sur le Bureau, les agents doivent apparaître à leur poste, sans
glisser vers lui.

## Contexte
Signalé par Benjamin le 30/10. En mode « Ajuster » (ticket-657), le zoom démarre à
100 % et ne se mesure qu'après le montage. `SolEtire` avait déjà activé la marche
(ticket-638) : le changement de largeur déplaçait les agents, et la transition
`.marche` animait ce déplacement. Une fenêtre redimensionnée produisait le même
effet.

## Fait
Quand l'étirement du sol change, `SolEtire` coupe la marche pendant une image :
le déplacement est immédiat, et les vraies marches restent animées. Retouche à
la main.

## Critères d'acceptation
- [x] `SolEtire.test.tsx` : un redimensionnement après l'activation de la marche la coupe, puis la réactive à l'image suivante
