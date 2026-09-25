---
id: ticket-175
title: "Neuf projets dans une liste plate, sans moyen de les ranger"
type: feat
status: done
pr_number: 27
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-25
---

# ticket-175 — Ranger les projets

## Objectif

Qu'une liste de projets reste lisible quand elle s'allonge.

## Contexte

Neuf projets aujourd'hui, dans une liste plate et sans ordre déclaré : des
dépôts clients, des projets personnels, le projet bootstrap, un banc d'essai.
Rien ne les distingue à l'écran, alors que ce qu'on en fait n'a rien à voir.

Le mélange a aussi une conséquence pratique : c'est dans cette liste qu'on
choisit sur quoi lancer un pipeline. Deux projets voisins aux noms proches,
et l'on se trompe de dépôt — exactement le risque qu'ADR-031 borne côté
écriture, pris par l'autre bout.

## Contrainte

La catégorie **se déclare**, elle ne se devine pas. Ni le nom du dossier, ni
l'URL du dépôt ne disent à quoi sert un projet : c'est le raisonnement
d'ADR-042 pour les commandes de lancement, et il vaut ici.

Un projet qui ne déclare rien reste visible — le défaut ne cache jamais.

## Solution proposée

`agents.json` porte une `category`, chaîne libre. La liste groupe par
catégorie, les projets sans catégorie formant leur propre groupe, en dernier.

## Critères d'acceptation

- [ ] Un projet déclare sa catégorie dans `agents.json`
- [ ] Un manifeste absent, illisible ou muet laisse le projet sans catégorie
- [ ] Une valeur qui n'est pas une chaîne est ignorée
- [ ] La liste groupe par catégorie, les sans-catégorie en dernier
- [ ] Les groupes sont ordonnés de façon stable
- [ ] Aucun projet ne disparaît, quelle que soit sa déclaration
- [ ] `uv run pytest`, `npx vitest run`, `tsc` et `eslint` passent

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

Une catégorie libre finira par contenir « Pro », « pro » et « PRO ». Assumé
pour l'instant : une liste fermée demanderait un réglage global, alors que la
déclaration vit dans le projet.
