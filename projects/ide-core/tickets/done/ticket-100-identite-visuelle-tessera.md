---
id: ticket-100
title: "L'application porte enfin son nom et sa marque"
type: feat
status: done
pr_number: 92
priority: medium
agent: codeur
depends_on: ["ticket-099"]
estimated_days: 1
created: 2026-09-21
---

# ticket-100 — L'application porte enfin son nom et sa marque

## Objectif

Donner à Tessera une identité visible : un titre d'onglet qui dit son nom, et
une icône dessinée pour lui — dans le navigateur comme sur le bureau.

## Contexte

ticket-099 a renommé le produit partout où le nom s'écrit : paquet Python,
crate Rust, identifiant Tauri, documentation. Il n'a pas touché à ce qui se
**voit**, parce que rien de tout ça ne contenait l'ancien nom — c'était pire
que faux, c'était générique :

- `frontend/index.html` affiche `<title>frontend</title>`. L'onglet du
  navigateur annonce donc le nom d'un dossier de build.
- `frontend/package.json` déclare `"name": "frontend"`.
- `frontend/public/favicon.svg` est le logo d'un template jamais remplacé — un
  éclair violet qui n'appartient pas au projet.
- `frontend/src-tauri/icons/` contient les quatorze fichiers livrés par défaut
  avec `tauri init`, tous datés du jour du scaffold.

Une tessera est la tuile taillée d'une mosaïque : la plus petite pièce qui,
posée à côté des autres, finit par faire une image. La marque retenue — « la
tuile détachée » — montre une pièce qui sort de la grille et passe devant,
ce qui est le geste du produit : un ticket extrait de la file, traité, reposé.

## Solution proposée

1. Dessiner la marque en SVG source dans `frontend/public/favicon.svg` :
   une grille 3×3 de tesselles en retrait, la tuile centrale pleine, agrandie
   et détachée. Géométrie sur une grille de 64, rayons de 2 et 3.
2. Les couleurs suivent ADR-026 : le violet est la couleur d'identité. La
   tuile pleine en violet, les voisines en violet désaturé. Deux jeux de
   valeurs, clair et sombre, via `prefers-color-scheme` dans la SVG.
3. `<title>Tessera</title>` dans `index.html`, `"name": "tessera"` dans
   `package.json`.
4. Régénérer le jeu d'icônes Tauri depuis une source 1024×1024
   (`npx tauri icon`), qui réécrit `icons/` en entier. La commande génère
   aussi les jeux iOS et Android : ils sont retirés, le projet ne cible que
   le desktop (ADR-004).
5. Un test verrouille le titre et le nom du paquet, pour la même raison
   qu'ADR-034 : un réglage que rien ne mesure redevient générique au ticket
   suivant.

Ce ticket **ne touche pas** à `CLAUDE.md`.

## Critères d'acceptation

- [ ] `frontend/index.html` contient `<title>Tessera</title>`
- [ ] `frontend/package.json` déclare `"name": "tessera"`
- [ ] `frontend/public/favicon.svg` ne contient plus la couleur `#863bff`
      du template d'origine
- [ ] `frontend/public/favicon.svg` définit un rendu distinct sous
      `prefers-color-scheme: dark`
- [ ] `frontend/src-tauri/icons/icon.png` diffère du fichier actuel et
      mesure 512×512 — la taille que produit `tauri icon`, la source étant
      en 1024
- [ ] `frontend/src-tauri/icons/` ne contient ni `android/` ni `ios/`
- [ ] Un test frontend échoue si `index.html` perd son titre ou si
      `package.json` reprend le nom `frontend`
- [ ] `npx tsc --noEmit` passe sans erreur
- [ ] `npm run test` passe en entier
- [ ] `npm run build` produit un `dist/` sans erreur

## Dépendances

ticket-099 — le renommage du produit, dont ce ticket finit la partie visible.

## Estimation

1 jour.

## Risques

`npx tauri icon` réécrit les quatorze fichiers de `icons/` d'un coup. Si la
source PNG est mal cadrée, la marque sera rognée dans tous les formats à la
fois, y compris `.icns` et `.ico` qu'on ne peut pas relire à l'œil ici. Le
cadrage se vérifie sur `128x128.png` avant de valider le lot.
