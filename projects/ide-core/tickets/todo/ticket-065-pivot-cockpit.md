---
id: ticket-065
title: "Pivot cockpit — l'IDE cesse d'imiter un éditeur et devient la console de la flotte"
type: refactor
status: todo
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

- [ ] La barre latérale gauche utilise **un seul jeu d'icônes**, chaque entrée
      portant un libellé visible (pas seulement au survol)
- [ ] Les actions d'un projet (lier à une forge, mode des artefacts, retirer de
      l'IDE, ouvrir dans VSCode) sont accessibles **sans scroller**, depuis un
      en-tête de projet
- [ ] Le centre de l'écran affiche par défaut les tickets et l'état du run en
      cours, pas un fichier
- [ ] Monaco est monté en `readOnly` et sert à lire un diff ; l'écriture via
      `PUT /fs/write` n'est plus déclenchée par l'UI
- [ ] Un arbre de fichiers minimal existe, branché sur `GET /fs/list`, en
      lecture seule — pour naviguer, pas pour travailler
- [ ] `npx tsc --noEmit` et `npm run test -- --run` verts

## Hors scope

- Recherche multi-fichiers, terminal intégré, git UI : c'est VSCode
- Toute refonte du backend
