---
id: ticket-133
title: "Amorcer la refonte de Carrière en application web multi-onglets"
type: design
status: todo
pr_number: null
priority: medium
agent: architect
depends_on: []
estimated_days: 1
created: 2026-09-23
---

# ticket-133 — Amorcer la refonte de Carrière en application web

## Objectif

Décider ce que devient `projects/carriere/` : aujourd'hui un dossier
d'analyses, demain une application consultable depuis n'importe quel poste.

## Contexte

`projects/carriere/CLAUDE.md` dit noir sur blanc : « Ce n'est pas un projet de
code. Aucun agent n'y écrit de programme ; ils lisent des documents et
produisent des analyses. » Le manifeste déclare `codeur` et `reviewer` avec un
prompt `analyste-carriere.md`.

En faire une webapp à onglets — gérer ses compétences, préparer un entretien
annuel, etc. — ne l'étend pas : ça le **refonde**. Deux natures cohabiteraient
dans un même projet, ou il en faut deux.

Le dépôt est déjà un dépôt git local, en mode `tracked`. Le relier à un dépôt
GitHub privé est un geste de quelques minutes, pas un chantier — mais il rend
public à un service tiers un contenu qui nomme un employeur, un contrat et une
clause d'exclusivité. Ça se décide, ça ne se fait pas en passant.

## Solution proposée

Trancher, dans l'ordre :

1. Un projet ou deux ? `carriere` (analyses, agents non-codeurs) et
   `carriere-app` (le code), ou un seul avec deux jeux d'agents.
2. Ce que l'application affiche : les analyses existantes rendues lisibles, ou
   des données saisies dans l'app — ce n'est pas la même chose à construire.
3. ~~Où elle tourne~~ — **tranché : local uniquement.** L'application tourne
   sur la machine ; le dépôt GitHub privé sert de synchronisation entre les
   deux postes, pas d'hébergement. Rien de ce que contient ce projet ne monte
   chez un tiers pour être servi.
4. Ce qui part sur GitHub privé et ce qui reste local, sachant qu'ADR-021 et
   ADR-023 ont un défaut fermé et qu'il existe une clause d'exclusivité
   documentée dans le projet.

## Un onglet identifié

**Générer un CV depuis des données structurées.** Étudié comme projet
autonome, puis rattaché ici : le parcours, les compétences et les missions
vivent déjà dans ce projet, et deux endroits qui décrivent la même carrière
finiraient par diverger. Entrée déterministe, sortie déterministe — c'est
aussi l'onglet le plus facile à tester.

## Critères d'acceptation

- [ ] Une décision écrite répond aux quatre questions ci-dessus
- [ ] La décision dit si `projects/carriere/CLAUDE.md` change de nature, et le
      ticket qui l'autorisera
- [ ] La liste des onglets de l'application est arrêtée, avec pour chacun une
      phrase disant à quelle question il répond
- [ ] La décision dit explicitement quels fichiers ne doivent pas partir sur
      GitHub, même privé
- [ ] Les tickets d'implémentation sont créés dans le projet concerné, pas
      dans `ide-core`

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

Le contenu de ce projet est sensible : contrat, rémunération, activité
freelance en parallèle d'un employeur qui exige une autorisation préalable.
« Privé » sur GitHub veut dire invisible du public, pas invisible du service.
