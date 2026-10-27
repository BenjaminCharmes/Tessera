---
id: ticket-593
title: "Office rooms get a floor and plants, the queue tooltip is no longer clipped, and the bottom bar uses the room's width"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: ["ticket-591"]
estimated_days: 0.5
created: 2026-10-27
---

# ticket-593 — Sol et plantes dans les pièces, infobulle entière, barre du bas lisible

## Objectif
Trois retours de Benjamin du 27/10 sur le Bureau (capture d'un run ide-core
avec 13 tickets en file).

## Contexte et corrections
1. **Infobulle de la file coupée** : l'infobulle de la pile
   (`components/BureauView/Dossiers.tsx`, `Infobulle`, `absolute bottom-full`)
   s'ouvre vers le haut à l'intérieur de la pièce, qui a `overflow-hidden`
   (`Piece.tsx`) : ses premières lignes sont coupées. Elle est rendue dans un
   portail (`createPortal` vers `document.body`), en position fixe calculée
   depuis la pile, et reste entière dans la fenêtre.
2. **Sol et plantes** : les salles de pause et de réunion ont un sol en
   lames (ticket-583), les pièces de travail non. Chaque pièce de travail
   reçoit le même sol, et un sprite `Plante.tsx` (sous `design/bureau/`,
   tons `--sprite-*`) se pose dans un coin de chaque pièce et de chaque salle.
   C'est du mobilier au sens de l'ADR-058 : fixe, sans animation, sans voyant.
3. **Barre du bas écrasée à gauche** : `ObjetsDeLaPiece.tsx` aligne la pile,
   la boîte aux lettres et la baie serrées à gauche. Les trois se répartissent
   sur la largeur (trois colonnes), chacune avec un libellé visible sous son
   sprite : « 13 en file » pour la pile ; pour la boîte, le libellé de
   `libelleDeLaBoite` (`lib/bureau/libelleDeLaBoite.ts`) sans son préfixe
   « Boîte aux lettres, » (« aucune PR », « PR #12 … ») ; pour la baie, les
   services comme aujourd'hui.

## Critères d'acceptation
- [ ] L'infobulle de la pile est rendue hors de l'élément de la pièce (portail vers `document.body`) ; un test vérifie qu'elle n'est pas descendante de la `section` de la pièce
- [ ] Chaque pièce de travail rend un sol et un sprite `plante` ; un test le vérifie
- [ ] Les salles de pause et de réunion rendent chacune un sprite `plante` ; un test le vérifie
- [ ] `Plante.tsx` est sous `design/bureau/`, sans classe d'animation ; `design/bureau/sources.test.ts` reste vert
- [ ] Sous la pile, le texte « 13 en file » s'affiche pour 13 tickets restants ; un test le vérifie
- [ ] Sous la boîte aux lettres d'une pièce sans PR, le texte « aucune PR » s'affiche ; un test le vérifie
- [ ] Le diff ne modifie aucun fichier de `backend/`
