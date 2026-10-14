---
agent: codeur
created: 2026-10-14
depends_on: []
estimated_days: 0.5
id: ticket-440
pr_number: null
priority: medium
status: done
title: The pipeline log at the bottom is collapsible, folded by default to one line
  with the latest event
type: feat
---

# ticket-440 — Le journal du pipeline se replie

## Objectif

Rendre au centre la hauteur que le journal occupe en permanence, tout en
gardant sous les yeux le dernier évènement.

## Contexte

Audit du 2026-10-14 : le panneau « Pipeline log » prend 180 px en bas de
chaque écran (`GRILLE_COCKPIT`, `frontend/src/design/layout.ts` :
`gridTemplateRows: "1fr 180px"`), y compris sur Projets, Statistiques ou
En cours où il ne sert pas. Maquette validée :
`projects/ide-core/design/maquette/Cadre.dc.html` (bouton Play : le
journal se déplie).

## Solution proposée

- Le panneau du bas (`components/BottomPanel/`) a deux états :
  - **replié** (défaut) : une barre de 32 px — « JOURNAL », une pastille
    bleue s'il y a un run en cours, le dernier évènement sur une ligne
    (tronqué), et « Déplier ▴ » ;
  - **déplié** : le journal actuel, 180 px, avec « Réduire ▾ ».
- La grille du cockpit suit : `auto` au lieu de `180px` pour la dernière
  rangée.
- L'état est mémorisé (stockage local), et un clic sur la barre bascule.

## Critères d'acceptation

- [ ] Un test vérifie que le panneau est replié par défaut et affiche le
      dernier évènement du journal
- [ ] Un test vérifie qu'un clic déplie le journal complet (`aria-expanded`
      passe à `true`) puis le replie
- [ ] Un test vérifie que l'état replié/déplié est relu du stockage local
- [ ] `layout.ts` ne fixe plus 180 px à la rangée du bas de `GRILLE_COCKPIT`

## Dépendances

Aucune.