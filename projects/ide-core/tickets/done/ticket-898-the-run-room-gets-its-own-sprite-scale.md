---
id: ticket-898
title: "The run room gets its own sprite scale, larger than the top rooms on a laptop"
type: fix
status: done
pr_number: 993
priority: medium
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-11-09
---

# ticket-898 — La pièce d'un run a sa propre échelle de sprites, plus grande que celle des salles du haut sur un portable

## Objectif

Que le mobilier et les agents de la pièce d'un run restent lisibles sur un
portable, au lieu de rétrécir comme ceux des quatre salles du haut.

## Contexte

Benjamin, le 09/11, sur son portable : « La vue du bureau est vraiment toute
petite (les meubles surtout sont minuscules alors que la salle a beaucoup de
place) ».

Le Bureau n'a qu'une échelle (`useEchelleDesSprites`), calculée pour que le mur
le plus chargé tienne dans **une** des quatre salles du haut, côte à côte
(`echellePourLargeur`, ticket-635). À 1 536 px, elle vaut 0,95. La pièce d'un run
s'étend sur la largeur des quatre salles et pose ses objets à des abscisses
relatives : la même échelle y laisse un mur et un sol presque vides.

Fait à la main, en retouche visuelle servie sur Vite 5175 (mémoire « retouches
UI en direct »), pendant qu'une file ide-core tourne dans le checkout.

## Solution

- `echelleDeLaPiece(echelleCommune)` dans `lib/bureau/echelleDesSprites.ts` :
  l'échelle commune multipliée par `FACTEUR_DE_LA_PIECE`, plafonnée à
  `ECHELLE_LARGE`, au vingtième.
- `FournisseurDEchelle` dans `hooks/useEchelleDesSprites.ts` : un contexte qui
  impose une échelle à tous les sprites qu'il contient ; sans lui, l'échelle
  commune.
- Seconde passe, même jour : `FACTEUR_DE_LA_PIECE` à 1,2 au lieu de 1,5, et
  `ECHELLE_LARGE` à 1,3 au lieu de 1,5, pour que tout soit moins gros et que la
  pièce et les salles se répondent sur les deux écrans.
- `Piece.tsx` calcule son échelle avec `echelleDeLaPiece` et enveloppe sa pièce
  dans `FournisseurDEchelle`.

## Critères d'acceptation

- [ ] `echelleDeLaPiece(echellePourLargeur(1536))` vaut 1,1 et ne dépasse jamais
      `ECHELLE_LARGE` ; `echelleDesSprites.test.ts` le vérifie.
- [ ] `ECHELLE_LARGE` vaut 1,3 : à 1,5, tout paraissait trop gros sur un
      27 pouces (Benjamin, seconde passe du 09/11).
- [ ] Les décalages des agents se proportionnent à `ECHELLE_DES_DECALAGES` (1,5,
      l'échelle à laquelle ils ont été réglés), plus au plafond.
- [ ] À 1 536 px, la fenêtre de la pièce d'un run est agrandie plus que celle
      d'une salle du haut ; `EchelleDuMur.test.tsx` le vérifie.
- [ ] Les salles du haut gardent l'échelle commune : le diff ne modifie ni
      `Salle.tsx` ni le calcul de `echellePourLargeur`, seulement son plafond.
- [ ] Captures à 1 536 et 1 920 px relues : aucun objet de la pièce ne se
      chevauche ni ne sort de la pièce.

## Ce que ça ne fait pas

- Ne change pas la disposition des salles du haut (pas de réagencement, choix de
  Benjamin du 03/11).
- Ne réintroduit pas de zoom réglable.
