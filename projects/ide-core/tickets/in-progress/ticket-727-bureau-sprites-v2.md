---
id: ticket-727
title: "The Bureau sprites v2 from the sprite workshop"
type: feat
status: in-progress
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

- [ ] Un module `frontend/src/lib/bureau/sprites/` porte le moteur, testé : un sprite
      donne un chemin par jeton, et le contour sélectif ne touche pas un jeton `etat-*`
- [ ] Les couleurs des sprites viennent de jetons `--sprite-*` définis dans
      `frontend/src/index.css`, redéfinis pour la nuit
- [ ] Les états (voyants, écrans) gardent les teintes d'ADR-026, jour comme nuit
- [ ] `sources.test.ts` vérifie le nouveau jeu de sprites
- [ ] Une ADR au prochain numéro libre de `memory/decisions.md` décrit le moteur et
      l'assouplissement cosmétique d'ADR-058, avec sa règle sous `## Proposées` de
      `contraintes.md`
- [ ] Benjamin a validé le rendu sur 5175 (captures 1920 et 1536)

## Dépendances

Aucune. La file ide-core tourne en parallèle : tests ciblés seulement pendant qu'elle
tourne.

## Estimation

3 jours, par lots.

## Risques

- Poids du DOM : un `<path>` par jeton et par sprite ; mesuré sur le pilote avant
  d'étendre.
- Calcul au rendu : mémoïsation obligatoire, la vue se relit toutes les 10 s.
