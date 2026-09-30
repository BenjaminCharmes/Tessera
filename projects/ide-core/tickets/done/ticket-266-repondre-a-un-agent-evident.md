---
agent: codeur
created: 2026-09-30
depends_on: []
estimated_days: 0.5
id: ticket-266
pr_number: null
priority: high
status: done
title: A run waiting for an answer comes first in Supervision, with a Reply button
  on its card
type: feat
---

# ticket-266 — Répondre à un agent se trouve sans chercher

## Objectif

Qu'un utilisateur qui voit « attend une réponse » sache immédiatement où
répondre.

## Contexte

Constaté le 2026-09-30 : trois runs en parallèle (ide-core, carriere-app,
freelance). Deux agents posaient une question. L'utilisateur voyait l'encadré
ambre de la carte, mais **ne trouvait pas où répondre** ; la réponse a dû être
envoyée hors de l'IDE.

Dans `components/SupervisionView/` :
- `RunCard.tsx` affiche la question et l'étiquette « attend une réponse » ;
- le champ de réponse (`AgentDialogue`, dans `AgentPanel`) n'est rendu que
  pour le run **sélectionné** ;
- la sélection par défaut est `runs[0]` (`index.tsx` :
  `runs.find(...) ?? runs[0]`), sans égard pour les runs qui attendent.

## Solution proposée

- Tri des cartes : les runs qui attendent une réponse d'abord, puis l'ordre
  actuel.
- Sélection par défaut : le premier run qui attend une réponse s'il y en a un,
  sinon le comportement actuel. Un choix explicite de l'utilisateur
  (`selectionner`) garde la priorité.
- Sur une carte qui attend : un bouton « Répondre » qui sélectionne le run et
  place le focus dans le champ de réponse d'`AgentDialogue`.
- Couleurs ADR-026 : l'attente reste `amber` ; le bouton est une action
  principale (fond violet), jamais du violet en texte.

## Critères d'acceptation

- [ ] Un test montre que, de deux runs dont le second attend une réponse, la
      carte du second est rendue en premier.
- [ ] Un test montre que, sans sélection explicite, le panneau de détail
      affiche le run qui attend une réponse.
- [ ] Un test montre qu'après un clic sur une autre carte, la sélection reste
      sur celle-ci même si un run attend.
- [ ] Un test montre que le bouton « Répondre » d'une carte en attente
      sélectionne son run et donne le focus au champ de réponse.

## Dépendances

Aucune.

## Estimation

Une demi-journée. Frontend uniquement.

## Risques

`AgentPanel` est aussi modifié par les tickets 256 et 257 : si l'un d'eux est
mergé avant, repartir de `develop` à jour.