---
id: ticket-110
title: "Les widgets natifs du navigateur suivent le thème sombre"
type: feat
status: done
pr_number: 124
priority: low
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-21
---

# ticket-110 — Les widgets natifs du navigateur suivent le thème sombre

## Objectif

Que les barres de défilement et les autres éléments dessinés par le navigateur
cessent d'être clairs au milieu d'une interface sombre.

## Contexte

L'application est sombre de bout en bout — `bg-zinc-900` sur la racine, toute
la palette d'ADR-026 en découle. Mais le navigateur ne déduit **pas** le thème
des couleurs qu'on lui donne : sans déclaration `color-scheme`, il peint ses
widgets natifs selon le réglage du système.

Le résultat se voit surtout sur les barres de défilement, larges et claires
dans chaque panneau qui déborde. Il touche aussi le curseur de texte, les
champs de formulaire et les menus `select`, qu'aucune classe Tailwind ne
peut atteindre.

Ce n'est pas un défaut de palette : aucune couleur n'est fausse. C'est une
partie de l'interface que la feuille de style ne revendiquait pas.

## Solution proposée

1. `:root { color-scheme: dark; }` — la déclaration standard, qui suffit à
   elle seule pour le curseur, les champs et les menus.
2. Styler explicitement la barre de défilement, sur les deux syntaxes :
   `scrollbar-width` / `scrollbar-color` (standard, Firefox) et
   `::-webkit-scrollbar` (Chrome, Safari, Edge). Les deux sont nécessaires,
   aucune n'étant encore universelle.
3. Les couleurs viennent de la famille **neutre** : `zinc-700` au repos,
   `zinc-600` au survol. ADR-026 réserve le violet à l'identité — du violet
   sur une barre de défilement se lirait comme un état de plus.

Ce ticket **ne touche pas** à `CLAUDE.md`.

## Critères d'acceptation

- [ ] `frontend/src/index.css` déclare `color-scheme: dark` sur `:root`
- [ ] La barre de défilement est stylée dans les deux syntaxes, standard et
      `-webkit-`
- [ ] Les couleurs employées appartiennent à la famille `zinc` — aucune autre
      famille d'ADR-026 n'apparaît
- [ ] `.\scripts\tessera.ps1 verify` est vert de bout en bout

## Ce que ça ne fait pas

**Aucun thème clair.** L'application est sombre par choix, et `color-scheme`
l'affirme au lieu de le subir. Rendre le thème configurable est un autre
sujet, qui toucherait toute la palette.

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

`::-webkit-scrollbar` n'est pas standard et Firefox l'ignore : c'est pourquoi
les deux syntaxes coexistent plutôt que l'une remplacer l'autre. Si l'une
disparaissait des navigateurs, l'autre continuerait de tenir le rendu.
