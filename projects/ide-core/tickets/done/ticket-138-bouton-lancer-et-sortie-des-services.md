---
id: ticket-138
title: "Bouton Lancer le projet, et sa sortie dans la Supervision"
type: feat
status: done
pr_number: 161
priority: medium
agent: codeur
depends_on: ["ticket-137"]
estimated_days: 1
created: 2026-09-23
---

# ticket-138 — Bouton « Lancer le projet », et sa sortie

## Objectif

Démarrer et arrêter les services d'un projet depuis l'IDE, et voir ce qu'ils
écrivent, sans quitter la fenêtre.

## Contexte

ticket-137 pose le manifeste, le registre et les endpoints ; rien ne les
appelle. La vue Supervision de ticket-129 sait déjà afficher plusieurs choses
qui tournent en parallèle et s'abonner au détail de l'une d'elles — c'est
exactement la forme dont un service a besoin.

Un service n'est pas un run : il n'a ni ticket, ni étapes, ni verdict, et il
ne se termine pas tout seul. Les confondre dans la même carte donnerait un
chrono qui monte indéfiniment à côté de runs qui finissent.

## Solution proposée

**Là où on lance** : le panneau du projet, à côté de ce qui le décrit. Pas le
tableau des tickets — lancer un projet n'a rien à voir avec un ticket.

**Ce que le bouton montre** : « Lancer » quand rien ne tourne, « Arrêter »
sinon, et rien du tout quand le projet ne déclare aucun `services` — un bouton
désactivé sans explication fait chercher une panne qui n'existe pas.

**Dans la Supervision** : une section distincte des runs, une ligne par
service (nom, projet, état, durée). Sélectionner une ligne s'abonne à sa
sortie, comme pour un run.

**États** : dans les cinq familles d'ADR-026 — `blue` tant qu'il tourne,
`red` s'il s'arrête seul avec un code non nul, `zinc` à l'arrêt. Un service
qui meurt de lui-même doit se voir : c'est le cas où on va chercher les logs.

## Critères d'acceptation

- [ ] Le bouton n'apparaît pas pour un projet sans `services` déclarés
- [ ] Un test vérifie que le bouton appelle `start` puis bascule sur
      « Arrêter »
- [ ] Un test vérifie qu'un service arrêté de lui-même avec un code non nul
      s'affiche en `red`
- [ ] Un test vérifie que la Supervision liste les services séparément des
      runs
- [ ] Un test vérifie que sélectionner un service émet son abonnement
- [ ] `design/coherence.test.ts` et `design/identite.test.ts` passent sans
      modification
- [ ] Aucun fichier ajouté ne dépasse 200 lignes
- [ ] `npm run typecheck`, `npm run lint`, `npm run test` et `npm run build`
      passent

## Dépendances

ticket-137.

## Estimation

1 jour.

## Risques

`npm run typecheck` est le seul vrai type-check de ce dépôt : `tsconfig.json`
porte `"files": []` et des références de projet, donc `npx tsc --noEmit` ne
vérifie rien et passe au vert sur du code qui ne compile pas.
