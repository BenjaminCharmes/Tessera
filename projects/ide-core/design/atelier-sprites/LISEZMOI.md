# Atelier des sprites du Bureau

Source des sprites du Bureau (ticket-727, ADR-070) : les grilles de jetons `famille.ton`
(`src/`), les palettes (`src/palettes.js`) et les outils (`tools/`). Le moteur porté en
TypeScript vit dans `frontend/src/lib/bureau/sprites/` ; ce dossier-ci sert à dessiner et à
régénérer le thème.

## Régénérer le thème

Depuis ce dossier, après une modification des palettes :

```bash
node tools/theme.js ../../../../frontend/src/design/bureau/sprites-theme.css
```

Le fichier produit ne s'édite jamais à la main. Un état garde les teintes d'ADR-026 : les
rampes `etat-*` viennent de leur famille Tailwind, ce que `theme.test.ts` vérifie.

## Catalogue

`catalogue-v1.html` et `pages/` sont les planches de revue validées le 30/10/2026.
`tools/build.js` reconstruit `dist/`, ignoré par git.

Arrivé dans Tessera le 04/11/2026, avec son historique (auparavant un dépôt local à part).
