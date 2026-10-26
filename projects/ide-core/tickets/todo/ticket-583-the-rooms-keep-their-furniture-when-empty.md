---
id: ticket-583
title: "The break room and the meeting room keep their furniture when nobody is in them"
type: fix
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: ["ticket-581"]
estimated_days: 0.5
created: 2026-10-26
---

# ticket-583 — Les salles gardent leur mobilier quand elles sont vides

## Objectif
Que la salle de pause et la salle de réunion se voient comme des salles, même
vides : Benjamin ne les a jamais vues occupées (26/10), et un cadre de texte
« Personne en pause » ne se lit pas comme un lieu du Bureau.

## Contexte
- La maquette (`design/maquette/Bureau.dc.html`, sections « Salle de pause » et
  « Salle de réunion ») dessine chaque salle avec un sol en lames
  (`repeating-linear-gradient`, 132 px de haut) et, en salle de pause, une
  machine à café toujours présente, légendée « café ». Le ticket-564 a livré
  les salles en cadre de texte (`components/BureauView/Salle.tsx`), sans ce décor.
- ADR-058 précisé le 26/10 : le mobilier d'une salle est la salle elle-même,
  pas un état ; il se dessine toujours, mais ne s'anime pas et ne porte aucun
  voyant qui ferait croire à une activité.

## Solution proposée
- Deux sprites SVG inline sous `design/bureau/` : `MachineACafe.tsx` (celle de
  la maquette, **sans** la vapeur ni le voyant vert) et `TableDeReunion.tsx`
  (la table de la maquette, sans personnage ni feuilles de diff), tons en
  jetons `--sprite-*`.
- `Salle.tsx` reçoit le mobilier en prop et dessine le sol et le mobilier,
  occupée ou non ; les occupants se placent à côté. Quand la salle est vide,
  la phrase `vide` reste, en dessous du mobilier.
- L'en-tête de chaque salle porte la phrase de la maquette : « attend quelque
  chose d'extérieur : quota, CI, une dépendance » et « conflit de rebase ».

## Critères d'acceptation
- [ ] Une salle de pause vide rend la machine à café (`aria-hidden`) et la phrase « Personne en pause » ; un test le vérifie
- [ ] Une salle de réunion vide rend la table et la phrase « Aucun conflit en cours » ; un test le vérifie
- [ ] Une salle occupée rend toujours son mobilier, et ses occupants ; un test le vérifie pour la salle de pause
- [ ] Les deux sprites sont sous `design/bureau/`, n'utilisent que des jetons `--sprite-*`, et n'ont ni classe d'animation ni teinte `green` ; le test `design/bureau/sources.test.ts` les couvre
- [ ] Le diff ne modifie aucun fichier de `backend/`
