---
id: ticket-657
title: "The Bureau has its own zoom, with a fit-to-height mode, and its shared rooms group their furniture"
type: feat
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-10-28
---

# ticket-657 — Un zoom propre au Bureau

## Objectif
Voir toutes les pièces d'un coup quand plusieurs projets tournent, sans rendre
le reste de l'app illisible.

## Contexte
Le 28/10, Benjamin a dézoomé Chrome pour voir trois pièces sans défiler : le
Bureau rendait bien, mais le reste de l'app devenait inutilisable. À ce zoom,
le mobilier des salles du haut, réparti d'un bord à l'autre, laissait de grands
vides.

## Solution proposée
- `lib/bureau/zoomDuBureau.ts` : pas de 10 %, bornes 40-125 %, et un zoom
  « ajusté » qui fait tenir le contenu dans la hauteur disponible sans jamais
  dépasser 100 %.
- `hooks/useZoomDuBureau.ts` mémorise le mode et recalcule « ajusté » quand la
  vue ou son contenu change de taille.
- `CommandesDeZoom` (− / pourcentage / + / Ajuster) dans l'en-tête de la Supervision ;
  le zoom ne s'applique qu'au Bureau.
- Les salles du haut regroupent leur mobilier au centre.

## Critères d'acceptation
- [x] Un test de `zoomDuBureau` vérifie le pas et ses bornes, le zoom ajusté qui n'agrandit jamais, et la validation du mode mémorisé
- [x] Un test de la Supervision vérifie que « Dézoomer le Bureau » passe le Bureau à 90 %
- [x] Capture à 1920 × 950 relue : « Ajuster » fait tenir les salles du haut et deux pièces sans défilement

## Ce que ça ne fait pas
- Ne zoome pas la Liste ni les autres vues.
