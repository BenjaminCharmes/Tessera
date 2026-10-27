---
id: ticket-594
title: "A finished agent stays seated at full size with its cup, instead of a tiny standing figure"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: ["ticket-591"]
estimated_days: 0.25
created: 2026-10-27
---

# ticket-594 — L'agent qui a fini reste assis, à sa taille, tasse levée

## Objectif
Le 27/10, Benjamin trouvait « bizarre » l'agent qui a fini (ticket-591) :
debout et « tout petit » à côté de son bureau.

## Contexte
`design/bureau/Personnage.tsx`, `PersonnageDebout` : pour tenir dans la
grille 16 × 18 du poste (`Poste.tsx`), le personnage debout est dessiné à
la moitié de l'échelle du personnage assis (tête de 3 px de large contre 6,
corps de 3 contre 8), collé au bureau.

## Solution proposée
- Supprimer `PersonnageDebout`. L'agent `fait` est assis à son poste, à la
  même échelle que les autres, immobile (pas d'`anim-tape`), une tasse levée
  devant lui (pixels `zinc-200` près d'une main) ; la coche reste sur
  l'écran (`Coche`).
- Ce qui distingue les trois états reste lisible d'un coup d'œil :
  `libre` = assis, estompé, écran éteint ; `occupe` = assis, tape, écran
  allumé ; `fait` = assis, tasse levée, coche verte.
- `data-pose` vaut `"assis"` pour les trois et un attribut
  `data-tasse="true"` marque l'agent qui a fini.

## Critères d'acceptation
- [ ] `Personnage.tsx` n'exporte plus de pose `debout`, et aucun fichier de `frontend/src` n'emploie `pose="debout"`
- [ ] Un poste `fait` rend un `personnage` avec `data-pose="assis"` et `data-tasse="true"`, et la coche ; un test le vérifie
- [ ] Un poste `fait` ne porte pas la classe `anim-tape` ; un test le vérifie
- [ ] Les postes `libre` et `occupe` n'ont pas `data-tasse` ; un test le vérifie
- [ ] `design/bureau/sources.test.ts` reste vert
- [ ] Le diff ne modifie aucun fichier de `backend/`
