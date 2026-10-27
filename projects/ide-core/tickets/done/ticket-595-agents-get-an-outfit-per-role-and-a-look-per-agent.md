---
agent: codeur
created: 2026-10-27
depends_on:
- ticket-593
estimated_days: 0.5
id: ticket-595
plan: true
pr_number: null
priority: high
status: done
title: Office agents get an outfit per role and a look per agent, standing and seated
  at the same scale
type: feat
---

# ticket-595 — Une tenue par rôle, un physique par agent, une seule échelle

## Objectif
Premier ticket du « Bureau vivant », maquette validée par Benjamin le 27/10 :
`design/maquette/Bureau-vivant.dc.html`
(https://claude.ai/artifact/1bksL8hJjUhcgwrs7VtD7j). Aujourd'hui tous les
agents sont strictement identiques, et l'agent debout du ticket-591 est
dessiné à demi-échelle (« tout petit », 27/10).

## Ce que dit la maquette
- **Tenue par rôle** (`TENUES` dans la maquette) : codeur sweat à capuche
  violet, testeur blouse blanche, sécurité veste bleu nuit, reviewer chemise
  sarcelle et cravate, validateur gilet ambre. Couleur du haut et de son
  ombre (bras).
- **Physique par agent** (`physique(projet, rôle)`) : peau (5 tons), couleur
  de cheveux (6), coiffure (courte, longue, chignon, chauve), jupe ou
  pantalon. Tiré d'une graine stable `projet:rôle` : le même agent garde son
  physique d'un rendu et d'un run à l'autre.
- **Deux poses à la même échelle** : assis (grille 16 × 18 du poste) et debout
  (grille 12 × 20, 42 × 70 px), tête de 6 px de large dans les deux.

## Solution proposée
- `design/bureau/Personnage.tsx` prend `tenue` et `physique` en props, et
  dessine les variantes de la maquette (cheveux longs, chignon, chauve, jupe,
  cravate, capuche). Les couleurs sont des jetons `--sprite-*` du `@theme`
  (ADR-058) : un jeu par tenue, un par peau, un par couleur de cheveux.
- `lib/bureau/physique.ts` : `physique(projet, role)` déterministe, et
  `TENUES` par rôle.
- La pose debout du ticket-591 (`PersonnageDebout`) est redessinée à
  l'échelle de la maquette ; l'agent `fait` debout se place **à côté** de son
  poste, hors de la grille du bureau (le poste ne le contient plus).
- La pièce s'élargit à la largeur de la maquette (800 px de sol, défilement
  horizontal sous cette largeur).

## Critères d'acceptation
- [ ] `physique("ide-core", "codeur")` rend deux fois le même résultat, et `physique("kadoomi", "codeur")` en diffère sur au moins un trait pour ces deux projets ; un test le vérifie
- [ ] Les cinq rôles ont cinq couleurs de haut distinctes ; un test le vérifie
- [ ] Le personnage du reviewer porte un élément `data-detail="cravate"` et celui du codeur `data-detail="capuche"` ; un test le vérifie
- [ ] Les poses assise et debout dessinent une tête de même largeur (6 unités) ; un test le vérifie sur les `rect` de la tête
- [ ] Les couleurs des sprites sont des jetons `--sprite-*` ; `design/bureau/sources.test.ts` reste vert
- [ ] Le diff ne modifie aucun fichier de `backend/`