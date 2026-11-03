---
id: ticket-632
title: "The Bureau drops its day banner, and the room of the project running the IDE shows its servers on"
type: fix
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-10-28
---

# ticket-632 — Plus de bandeau du jour, et ide-core montre ses serveurs allumés

## Objectif
Retirer du Bureau ce qui n'informe pas, et y montrer juste l'état des serveurs de
l'IDE.

## Contexte
Retours du 28/10 :
- le bandeau « Dépense du jour / Session / Semaine » affichait le coût annoncé par
  le SDK au prix de l'API, sans rapport avec l'abonnement. Session et Semaine
  restaient vides : le SDK ne donne un relevé de quota que lorsque l'état change,
  et rien n'est conservé au redémarrage (`quota_registry.py`). Les coûts ont
  l'onglet Statistiques, et l'alerte de quota sa notification (ticket-555) ;
- dans la pièce d'ide-core, la baie montrait `backend` et `frontend` éteints, et
  « Lancer » était proposé. Tessera est lancé par `tessera.ps1`, hors du registre
  de services : « Lancer » démarrerait un second backend sur des ports déjà pris.
  Le projet porte pourtant `fait_tourner_l_ide` (ticket-152), que la colonne
  latérale respectait déjà.

## Solution proposée
- `TableauDuJour`, `FenetreDeQuota` et `useTableauDuJour` sont supprimés.
- `Piece.tsx` lit `fait_tourner_l_ide` : pas de `BoutonServices`, et la baie reçoit
  ses services allumés (`servicesDeLaBaie`).

## Critères d'acceptation
- [x] `BureauView` ne rend plus de tableau du jour
- [x] Un test de `servicesDeLaBaie` vérifie que les services du projet qui fait tourner l'IDE se montrent allumés, et que ceux d'un autre projet restent tels que le registre les lit
- [x] Un test de `Piece` vérifie que la pièce du projet qui fait tourner l'IDE n'offre pas « Lancer »

## Ce que ça ne fait pas
- Ne touche pas au backend : le quota reste relevé comme avant, pour la notification.
