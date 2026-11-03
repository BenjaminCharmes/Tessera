---
id: ticket-727
title: "The Bureau sprites v2 from the sprite workshop"
type: feat
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 3
created: 2026-11-02
---

# ticket-727 — Les sprites du Bureau v2, depuis l'atelier

## Objectif

Remplacer les sprites du Bureau par la refonte validée le 30/10 dans l'atelier
(`Desktop/atelier-sprites`) : grille ×2, rampes de quatre tons, contour sélectif,
jour Tessera ou Chaud par matière, nuit Néon.

## Contexte

L'atelier dessine 67 sprites avec un moteur JS (`engine.js`) : chaque pixel porte un
jeton (`famille.ton`), jamais une couleur, et le rendu émet un `<path>` par jeton.
Benjamin a validé le rendu (« tout me semble parfait ») et ses votes de jour sont dans
`JOUR_PAR_DEFAUT`. Le cosmétique est accepté : il assouplit ADR-058, qui reste en
vigueur pour tout ce qui rend un état.

Chantier mené **à la main, hors pipeline** (exception propre à ce chantier, décidée le
30/10) : le pipeline ne sait pas relire une branche déjà écrite, et la file ide-core
tourne en parallèle.

## Solution proposée

- Porter le moteur en TypeScript sous `frontend/src/lib/bureau/sprites/` : grille,
  cuisson (liseré, contour sélectif), sortie en chemins par jeton. Les sprites se
  calculent au rendu, mémoïsés par props ; `fill="var(--sprite-<famille>-<ton>)"`.
- Les rampes deviennent des jetons `--sprite-*` du `@theme` (`index.css`), redéfinis
  pour la nuit : changer d'heure ne coûte que des variables CSS.
- Par lots, un commit chacun : tête et poste en pilote (poids du bundle et rendu réel
  mesurés), sols et murs, pièce de run, serveurs, communs, nouveautés (visages, marche,
  lueur de nuit). Reporter les positions modifiées (tableau, cadre, plafonniers, meuble
  bas du café). Adapter `sources.test.ts`.
- Revue visuelle de Benjamin sur Vite 5175, captures 1920 et 1536.

## Critères d'acceptation

- [x] Un module `frontend/src/lib/bureau/sprites/` porte le moteur, testé : un sprite
      donne un chemin par jeton, et le contour sélectif ne touche pas un jeton `etat-*`
- [x] Les couleurs des sprites viennent de jetons `--sprite-*` de
      `frontend/src/design/bureau/sprites-theme.css`, importé par `index.css`,
      redéfinis pour la nuit
- [x] Les états (voyants, écrans) gardent les teintes d'ADR-026, jour comme nuit
- [x] `sources.test.ts` vérifie le nouveau jeu de sprites
- [x] Une ADR au prochain numéro libre de `memory/decisions.md` (ADR-070) décrit le
      moteur et l'assouplissement cosmétique d'ADR-058 ; sa règle, acceptée par
      Benjamin le 03/11, remplace celle d'ADR-058 dans `## Interface et design` de
      `contraintes.md`
- [x] Benjamin a validé le rendu sur 5175 (03/11, « on valide tout »)

## Dépendances

Aucune. La file ide-core tourne en parallèle : tests ciblés seulement pendant qu'elle
tourne.

## Estimation

3 jours, par lots.

## Risques

- Poids du DOM : un `<path>` par jeton et par sprite ; mesuré sur le pilote avant
  d'étendre.
- Calcul au rendu : mémoïsation obligatoire, la vue se relit toutes les 10 s.

## Ce que ça ne fait pas

- Pas de zoom : essayé puis retiré à la demande de Benjamin (03/11). Le Bureau et
  « En cours » prennent toute la largeur, le reste se voit en défilant.
- `design/bureau/sprites-theme.css` se régénère avec `tools/theme.js` de l'atelier
  (`Desktop/atelier-sprites`), hors du dépôt.
- Les contrôles de chevauchement et de débordement des salles se font en navigateur
  (Playwright), pas en vitest : jsdom ne calcule aucune mise en page.
