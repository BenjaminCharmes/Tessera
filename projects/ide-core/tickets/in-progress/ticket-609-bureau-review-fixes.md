---
id: ticket-609
title: "Bureau review fixes: one scale everywhere, wall and floor, one sun, a light switch, the thread in the List"
type: fix
status: in-progress
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-27
---

# ticket-609 — Retouches du Bureau après la passe de Benjamin

## Objectif

Corriger ce que Benjamin a relevé le 27/10 sur le Bureau terminé (597 à 607),
en une itération faite à la main et relue par lui avant le merge.

## Contexte

Ses retours, un par point :

1. Les pièces des projets sont à une autre échelle que les salles du haut : le
   sol de 800 px était agrandi par `zoom` (ticket-606), les personnages aussi.
2. Le mode compact rétrécit les pièces : garder toute la largeur, empiler, défiler
   en hauteur.
3. Avec un seul projet, un petit défilement vertical inutile.
4. Le chignon se lit mal.
5. Un agent en pause sans tasse garde les bras levés.
6. Fenêtres trop près du plafond, plante minuscule.
7. Pas de distinction entre le mur et le sol.
8. Pas d'interrupteur pour allumer ou éteindre à la main.
9. Plusieurs fenêtres, plusieurs soleils.
10. « Fil » ouvre un panneau sous le Bureau, qui en mange la moitié, alors que la
    Liste existe à un clic.
11. Le tableau blanc liste ses critères en un bloc difficile à lire.

## Solution

- Le sol garde son repère de 800 px mais ne grossit plus : `SolEtire` étire les
  abscisses (`etirementDuSol`), les sprites gardent la taille des salles communes.
  Le mur pose ses objets en pourcentage du repère.
- Plus de mode compact : une pièce par projet, empilées.
- Mur (`--sprite-mur`) au-dessus d'une plinthe, sol en lames dessous, dans les
  pièces et les salles ; fenêtres descendues, plante de 40 × 50.
- Coiffure `carre` à la place du chignon ; activité `pause`, bras le long du
  corps, à la place de `etire` ; les bras levés restent pour la fête.
- Un seul soleil, au bureau du directeur ; nuages tirés par salle et par jour
  (`cielDesFenetres`).
- Interrupteur par salle (`useLumiere`), préférence du navigateur, oubliée au
  changement de moment de la journée ; la nuit sans lumière, voile plus sombre.
- « Fil » sélectionne le run et bascule sur la Liste.
- L'infobulle du tableau blanc : une ligne par critère, puce d'état, identifiants
  en police fixe, plus large.

## Critères d'acceptation

- [ ] `SolEtire.tsx` n'utilise ni `zoom` ni `transform: scale` ; un test vérifie `data-etirement="1.5"` à 1200 px.
- [ ] `BureauView/index.tsx` n'importe plus `Compact` ni `modeCompact` ; un test rend sept pièces empilées.
- [ ] `Tete.tsx` ne connaît plus `chignon` ; un test vérifie les deux mèches du carré.
- [ ] Un test vérifie un seul soleil, dans le bureau du directeur.
- [ ] Un test vérifie que l'interrupteur allume une pièce le jour et assombrit le voile la nuit.
- [ ] Un test vérifie que « Fil » appelle `selectionner` et bascule sur la Liste.

## Ce que ça ne fait pas

- Le point 3 (défilement avec un seul projet) n'a pas de code à lui : il venait de
  la hauteur ajoutée par le `zoom`, qui a disparu.
