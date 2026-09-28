---
agent: codeur
created: 2026-09-21
depends_on:
- ticket-100
estimated_days: 1
id: ticket-101
pr_number: null
priority: medium
status: done
title: La marque se lit là où elle est posée
type: feat
---

# ticket-101 — La marque se lit là où elle est posée

## Objectif

Faire que la marque de Tessera se lise partout où elle apparaît — dans
l'onglet du navigateur comme dans l'application.

## Contexte

ticket-100 a dessiné la marque et l'a posée. Deux constats à l'usage.

### 1. Dans l'onglet, il ne reste qu'un carré

Le pavement disparaît. Ce n'est pas une impression : les rapports de
contraste de `favicon.svg` contre les fonds réels le disent.

| Couleur | Onglet sombre | Page sombre | Onglet clair | Blanc |
|---|---|---|---|---|
| `.pose` clair `#ddd6f6` | 8.63 | 11.52 | **1.07** | 1.40 |
| `.pose` sombre `#3a3348` | **1.00** | 1.34 | 9.17 | 12.02 |

Le pavement sombre est à **1.00** contre la barre d'onglets de Chrome —
contraste nul au sens littéral. Le pavement clair est à **1.07** contre la
barre d'onglets claire : le mode clair est aussi cassé, il n'avait pas été
remarqué.

La cause est une erreur de référence. Les deux jeux de couleurs ont été
validés contre le fond de la **page** — `zinc-900`, blanc — alors que le
navigateur pose le favicon sur une **barre d'onglets** dont le gris est
intermédiaire dans les deux thèmes.

S'y ajoute un piège qu'aucun ajustement de valeur ne corrige :
`prefers-color-scheme` dans un favicon SVG suit le thème de **l'OS**, pas
celui du navigateur. Il y a quatre combinaisons OS × navigateur, la media
query n'en distingue que deux. Un Windows clair avec Chrome sombre reçoit les
couleurs claires sur un fond sombre. **La lisibilité ne peut donc pas reposer
sur la media query.**

Une palette unique de luminance médiane a été testée : elle tient sur les
quatre fonds, mais l'écart entre le pavement et la tuile tombe à **1.31** —
la tuile détachée cesse de se distinguer et la marque devient un carré plein.
Elle achète la lisibilité en supprimant ce que ticket-100 voulait montrer.

D'où le choix retenu : à 16px, huit tesselles de 4px ne se lisent pas, avec ou
sans contraste. Le favicon porte une version **simplifiée**, la marque
complète restant celle de l'application et du bureau.

### 2. Dans la page, le produit ne se nomme nulle part

`App.tsx` dispose une grille de deux lignes sans bandeau : aucun en-tête
global n'existe. Le sommet du `NavRail` — colonne de 100px sur toute la
hauteur — est vide (`pt-2` puis les destinations). C'est le seul emplacement
qui ne coûte de hauteur à aucun panneau ; un bandeau global en prendrait à
tous.

## Solution proposée

1. **Simplifier `frontend/public/favicon.svg`** : la tuile détachée et son
   jour restent le sujet ; le pavement est allégé — **jamais supprimé** : sans
   lui il ne reste qu'un carré, et la marque ne dit plus rien —, la tuile
   occupant la place gagnée. Le dessin doit se lire à 16px.
2. **Choisir les couleurs contre les quatre fonds**, pas contre la page. Le
   plafond mathématique d'une couleur unique servant à la fois le blanc et le
   presque-noir est **3.03:1** : la marge est étroite et le seuil du critère
   en tient compte. Valeur repère mesurée à 3.03 sur les quatre fonds :
   `#9d63de`.
3. **Conserver la media query** comme raffinement esthétique — mais chaque
   jeu de couleurs doit passer le seuil **seul**, puisque l'OS et le
   navigateur peuvent diverger.
4. **Conserver la marque complète** dans `frontend/src-tauri/icon-source.svg`.
   Les quatorze icônes de `icons/` ne sont pas régénérées : elles ne sont
   jamais posées sur une barre d'onglets.
5. **Ajouter une zone d'identité au sommet du `NavRail`** : la marque puis
   « Tessera » en dessous, dans un bloc aligné sur `BAND` (`h-10`, ticket-067)
   et séparé des destinations. ADR-026 impose que l'accent d'identité soit une
   **barre, jamais la couleur d'un mot** : le nom se rend en neutre.

Ce ticket **ne touche pas** à `CLAUDE.md`, ni à la palette d'états d'ADR-026,
ni aux icônes desktop.

## Critères d'acceptation

- [ ] Un test calcule le rapport de contraste WCAG de chaque couleur portant
      une forme dans `favicon.svg` contre les quatre fonds de référence
      `#35363a`, `#202124`, `#dee1e6`, `#ffffff`, et échoue sous **2.5:1**
- [ ] Le test couvre les **deux** jeux de couleurs, clair et sombre, chacun
      évalué seul contre les quatre fonds
- [ ] `frontend/src-tauri/icon-source.svg` contient toujours les huit
      tesselles du pavement — la marque complète n'est pas simplifiée
- [ ] Les quatre tests de `frontend/src/design/identite.test.ts` passent
      encore, y compris celui qui exige `prefers-color-scheme: dark`
- [ ] Le `NavRail` rend le texte « Tessera », vérifié par un test RTL
- [ ] Le nom rendu ne porte aucune classe `text-violet-*`, vérifié par un test
      (ADR-026 : l'accent d'identité est une barre, pas un mot coloré)
- [ ] Le `NavRail` rend toujours ses six destinations, aucune régression
- [ ] `.\scripts\tessera.ps1 verify` est vert de bout en bout

## Dépendances

ticket-100 — qui a posé la marque que celui-ci rend lisible.

## Estimation

1 jour.

## Risques

Le seuil de 2.5:1 est proche du plafond atteignable de 3.03:1. Une couleur
choisie hors de la bande étroite de violets qui conviennent échouera au test
sans que le dessin soit en cause — la valeur repère du point 2 existe pour
éviter d'avoir à la chercher.

Simplifier le favicon éloigne le dessin de l'onglet de celui du bureau. C'est
assumé : ce sont deux tailles de rendu qui n'ont jamais eu les mêmes
contraintes, et `icon-source.svg` reste la référence de la marque.