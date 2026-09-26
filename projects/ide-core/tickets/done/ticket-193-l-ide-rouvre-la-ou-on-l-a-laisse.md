---
id: ticket-193
title: "L'IDE rouvre là où on l'a laissé"
type: feat
status: done
pr_number: 57
priority: medium
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-09-26
---

# ticket-193 — L'IDE rouvre là où on l'a laissé

## Objectif

Qu'un rechargement de page ou un redémarrage de l'app retrouve le projet
actif, le panneau ouvert, l'onglet de droite et la vue centrale.

## Contexte

Tout l'état d'interface vit dans des `useState` (`useActiveProject.ts:12`,
`App.tsx:34,53`). Il n'y a aucun `localStorage` dans `frontend/src`. Depuis
les tickets 183 et 185, un F5 retrouve le run et son texte — mais retombe
sur le premier projet de la liste, avec le panneau par défaut. Avec six
projets, c'est un clic ou deux à chaque fois, plusieurs fois par jour.

## Solution proposée

- Un hook `useEtatPersistant<T>(cle, defaut)` qui lit et écrit une clé
  `tessera.ui.<cle>` dans `localStorage`, avec `try/catch` sur chaque accès
  (mode privé, stockage bloqué) et repli sur le défaut.
- Y passer : projet actif, panneau de la barre latérale, onglet de droite,
  vue centrale, réglage des notifications (ticket-192).
- Un projet mémorisé qui n'existe plus retombe sur le premier de la liste,
  sans erreur.
- **Pas** de persistance de l'état d'un run ni du texte des agents : c'est
  le backend qui le tient (tickets 183, 185), et deux sources divergeraient.

## Critères d'acceptation

- [ ] Un test vérifie qu'un projet actif est relu après un remontage du
      composant
- [ ] Un test vérifie qu'un projet mémorisé absent de la liste retombe sur le
      premier, sans erreur console
- [ ] Un test vérifie qu'un `localStorage` qui lève ne casse pas le rendu
- [ ] Le `Sidebar`, l'onglet droit et la vue centrale sont restaurés
- [ ] `npm run test` et `npm run build` passent

## Ce que ça ne fait pas

Pas de synchronisation entre machines, pas de profils.

## Dépendances

Aucune.

## Estimation

Une demi-journée.

## Risques

Aucun notable.
