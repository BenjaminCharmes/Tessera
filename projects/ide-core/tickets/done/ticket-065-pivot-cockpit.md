---
id: ticket-065
title: "Pivot cockpit — l'IDE cesse d'imiter un éditeur et devient la console de la flotte"
type: refactor
status: done
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 4
created: 2026-09-16
---

# ticket-065 — Pivot cockpit

## Pourquoi

vibe-ide a été construit ticket par ticket, et chaque feature a poussé son
panneau. D'où une barre latérale d'icônes hétéroclites où rien n'annonce ce sur
quoi on clique, des actions projet reléguées en bas d'un scroll, et un éditeur
Monaco qui occupe le centre de l'écran sans jamais pouvoir rivaliser avec
VSCode — ni LSP, ni debugger, ni recherche multi-fichiers, ni terminal.

La valeur de vibe-ide n'est pas d'éditer du texte : c'est d'orchestrer une
chaîne d'agents avec des gates, sur des tickets qui survivent aux sessions.
L'UI doit montrer **ça**, et laisser l'édition à VSCode.

## Décision

L'écran principal cesse d'être un éditeur. Il montre l'état de la flotte :
tickets, runs, diffs. Monaco reste, en **lecture seule**, comme lecteur de diff
— il coûte peu et évite de basculer vers VSCode pour relire ce qu'un agent a
produit. L'écriture passe par VSCode, ouvert d'un clic depuis le projet.

## Critères d'acceptation

- [x] La barre latérale gauche utilise **un seul jeu d'icônes**, chaque entrée
      portant un libellé visible (pas seulement au survol)
- [x] Les actions d'un projet (lier à une forge, mode des artefacts, retirer de
      l'IDE, ouvrir dans VSCode) sont accessibles **sans scroller**, depuis un
      en-tête de projet
- [x] Le centre de l'écran affiche par défaut les tickets et l'état du run en
      cours, pas un fichier
- [x] Monaco est monté en `readOnly` et sert à lire un diff ; l'écriture via
      `PUT /fs/write` n'est plus déclenchée par l'UI
- [x] Un arbre de fichiers minimal existe, branché sur `GET /fs/list`, en
      lecture seule — pour naviguer, pas pour travailler
- [x] `npx tsc --noEmit` et `npm run test -- --run` verts

## Hors scope

- Recherche multi-fichiers, terminal intégré, git UI : c'est VSCode
- Toute refonte du backend

## Livré

- `NavRail` remplace `IconBar` : icônes tracées en SVG sur une seule grille de
  24, au même trait, libellé visible sous chacune (`643bce7`)
- `ProjectHeader` épingle les actions du projet au-dessus de la colonne qui
  défile, et ouvre le projet dans VSCode par `vscode://file/` (`6ea240d`)
- `FileTree` en lecture seule sur `GET /fs/list`, chargement paresseux par
  dossier ; Monaco monté `readOnly`, plus aucun `PUT /fs/write` déclenché par
  l'UI ; le tableau des tickets est la vue par défaut du centre (`31a0de0`)

## Constat en marge

`npm run build` échouait déjà sur `develop` avant ce ticket : 36 erreurs TS,
toutes dans des fichiers de test, que `npx tsc --noEmit` ne voit pas. Ce ticket
en a corrigé 11 au passage ; il en reste 25, hors périmètre ici.
