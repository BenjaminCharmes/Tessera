---
id: ticket-735
title: "Brush stroke: a softer, French, friendlier interface"
type: feat
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 2
created: 2026-11-02
---

# ticket-735 — Coup de pinceau : une interface plus douce, en français, plus accueillante

## Objectif
Harmoniser et moderniser l'interface sans changer son identité : moins brute, plus
lisible, des graphiques soignés. Fait à la main avec Benjamin, en direct sur un Vite à
part (audit UX du 02/11, maquette `projects/ide-core/design/maquette/coup-de-pinceau/`).

## Ce qui change
- Base : texte lissé, barres de défilement fines, transitions courtes sur ce qui se
  clique, entrée en fondu des vues (`entree-de-vue`), coupées sous `prefers-reduced-motion`.
- Titres de région en casse normale ; cartes et tuiles plus douces (coins, bordure, ombre).
- Graphiques : barres fines arrondies qui poussent, courbes avec aire qui se dévoilent,
  grille pointillée, anneau plus grand qui s'ouvre.
- Une vue de projet sans projet choisi propose les projets, avec leurs icônes
  (`ChoixDuProjet`), au lieu d'une coquille vide.
- Le français partout à l'écran : `lib/libelles.ts` (statuts, priorités, types, statuts
  de run) ; kanban, filtres, création de ticket, runs récents, historique, résumé.
- Statistiques : squelettes à la forme de la page pendant la lecture.
- Rail : une barre d'identité devant l'élément actif.

## Critères d'acceptation
- [x] `ChoixDuProjet.test.tsx` couvre l'écran de choix et ses icônes
- [x] `StatsView.test.tsx` vérifie les squelettes pendant la lecture
- [x] Les tests des cartes, du kanban et de l'historique lisent les libellés français
- [x] Benjamin a validé le rendu sur 5176 (« je valide tout »)

## Ce que ça ne fait pas
- Le journal du bas reste ouvert quand rien ne tourne : à reprendre dans un ticket.
