---
id: ticket-411
title: "Each project card in the Projects view can start or stop the project's app without leaving the view"
type: feat
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: ["ticket-410"]
estimated_days: 0.5
created: 2026-10-13
---

# ticket-411 — Démarrer l'app d'un projet depuis sa carte

## Objectif

Lancer ou arrêter l'app de plusieurs projets d'affilée depuis la vue Projets,
sans être envoyé sur les tickets de chacun.

## Contexte

Signalé par Benjamin le 2026-10-13 : un clic sur une carte
(`components/ProjetsView/ProjetCarte.tsx`) ouvre les tickets du projet ;
pour en démarrer un deuxième, il faut revenir à la vue Projets. Le
ticket-410 fournit `services_declares` et `services_en_cours` dans la vue
d'ensemble. Les appels existent déjà : `api.services.start` /
`api.services.stop` (`lib/api.ts`).

## Solution proposée

- Sur `ProjetCarte`, quand `services_declares` est vrai : un bouton
  « Lancer » (ou « Arrêter » quand `services_en_cours`), dans la rangée du
  bas de la carte, au style des boutons secondaires de l'en-tête de projet.
- Le clic appelle `start` ou `stop`, **arrête la propagation** (la carte
  n'est pas sélectionnée, la vue ne change pas), désactive le bouton pendant
  l'appel, puis demande à `ProjetsView` de relire la vue d'ensemble.
- Échec : message court sous le bouton, en `red` (ADR-026), la carte reste
  utilisable.
- Pas de bouton sans service déclaré.

## Critères d'acceptation

- [ ] Un test vérifie qu'un clic sur « Lancer » appelle `api.services.start`
      avec l'id du projet et **n'appelle pas** `onSelect`
- [ ] Un test vérifie que le bouton affiche « Arrêter » quand
      `services_en_cours` est vrai, et appelle `api.services.stop`
- [ ] Un test vérifie qu'aucun bouton n'apparaît quand `services_declares`
      est faux
- [ ] Un test vérifie qu'un échec de l'appel affiche un message et laisse le
      bouton réactivé
- [ ] Un test de `ProjetsView` vérifie que la vue d'ensemble est relue après
      un lancement réussi

## Dépendances

ticket-410.
