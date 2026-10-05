---
name: design-ui
description: Use when creating or modifying any user interface — screens, components, layouts, or styles.
---

# Design d'interface

## 1. Charte d'abord

Avant d'écrire la moindre ligne d'UI, cherche la charte du projet :

- **Tokens** : variables CSS ou blocs `@theme` dans `index.css` (ou équivalent).
- **Justification** : `memory/design.md`.

Si la charte existe, n'en sors sur aucune valeur — ni couleur, ni taille, ni
rayon, ni espace. Si elle n'existe pas, écris-la **avant** de toucher à l'UI.
La charte contient, dans cet ordre :

1. Une direction en une phrase, avec une référence nommée et ce qu'on en retient
   (ex. : « Linear — densité et monochrome avec un seul accent bleu »).
2. Au plus cinq familles de couleurs, chacune avec un rôle unique
   (fond, texte, état, identité, donnée).
3. Une échelle typographique : les tailles nommées et leurs usages.
4. Une échelle d'espacement et les valeurs de rayon retenues.
5. Le thème déclaré au navigateur, clair ou sombre (voir §3).

## 2. Aucune valeur en dur

Hors des tokens, rien. Pas de `#3b82f6`, pas de `text-[13px]`, pas de
`p-[18px]`. Si un token manque, l'ajouter à la charte avant de l'utiliser.

## 3. Thème du navigateur

Le navigateur ne déduit pas le thème des couleurs CSS : sans `color-scheme`,
il peint scrollbars, champs, menus `select` et curseur dans **sa** préférence.
Une app sombre ouverte dans un navigateur clair garde des scrollbars blanches.

- Déclarer `:root { color-scheme: dark; }` (ou `light`) : la valeur suit la
  **charte**, jamais le système.
- Une charte à deux thèmes bascule `color-scheme` avec sa classe ou sa media
  query, en même temps que ses couleurs.
- Styler les scrollbars (`scrollbar-color`, `::-webkit-scrollbar-*`) avec les
  tokens de surface et de bordure. L'accent s'y lirait comme un état de plus.

## 4. Défauts à éviter

Ces choix sont les plus probables pour un modèle sans contrainte ; ils sont
tous interdits sauf décision explicite de la charte :

- **Dégradé décoratif** (`bg-gradient-to-r …`) : signe de remplissage, pas de
  direction.
- **Cartes ombrées partout** (`shadow-lg` sur chaque bloc) : la hiérarchie doit
  venir de l'espace et de la couleur, pas de l'ombre.
- **Emojis en guise d'icônes** : incohérents entre systèmes, non redimensionnables.
  Utiliser un jeu d'icônes SVG cohérent.
- **Tout centré** : les vues de travail se lisent de gauche à droite.
- **Une couleur différente par section** : la dérive commence ici. Cinq familles,
  pas plus.

## 5. Hiérarchie

- Une seule action principale par vue — le bouton le plus visible appelle
  l'action la plus fréquente.
- Chaque vue prévoit ses trois états : **vide** (message d'invitation, pas de
  tableau vide), **chargement** (indicateur non bloquant), **erreur** (message
  lisible avec une sortie possible).
- Contraste minimum AA : 4,5:1 pour le texte courant, 3:1 pour les grandes
  tailles et les composants.

## 6. Densité

Une vue de travail montre des données, pas des marges. L'espace sert à
séparer des groupes, pas à remplir l'écran. Règle de décision : si tu peux
montrer deux fois plus d'éléments sans écraser le texte, l'espacement est
trop généreux.
