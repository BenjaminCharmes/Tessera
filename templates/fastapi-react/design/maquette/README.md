# Maquette validée

Ce dossier accueille la maquette de l'interface, une fois validée. Tant qu'il
ne contient que ce fichier, le projet n'a pas de maquette : l'interface
s'écrit d'après la charte (`memory/design.md`).

## D'où vient une maquette

Elle se dessine avec le développeur, hors pipeline, dans l'éditeur de
maquettes de Claude : un fichier `.dc.html` par écran, versionné ici. Un agent
du produit n'a pas accès à cet éditeur et ne la produit pas.

## Comment la lire

Un fichier `.dc.html` est du HTML ordinaire avec des styles en ligne, plus
quelques balises propres à l'éditeur (`<x-dc>`, `<sc-for>`, `<sc-if>`, une
valeur entre doubles accolades) et une classe `Component` qui fournit les
données d'exemple. Il ne s'ouvre pas seul dans un navigateur : il se **lit**
comme référence.

## Ce qui fait foi

- **La structure** : l'ordre des blocs, les tailles, les espacements et les
  états (vide, chargement, erreur, sélection, etc.) se reproduisent tels quels.
- **Les couleurs deviennent des tokens** : chaque couleur en dur de la
  maquette est remplacée par le token correspondant de la charte
  (`memory/design.md`, `@theme` de `index.css`). Aucune valeur en dur n'entre
  dans le code.
- **Les textes d'exemple sont des données**, pas du contenu à recopier.
