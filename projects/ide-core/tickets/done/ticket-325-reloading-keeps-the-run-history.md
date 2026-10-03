---
agent: codeur
created: 2026-10-02
depends_on: []
estimated_days: 1
id: ticket-325
plan: true
pr_number: 230
priority: high
status: done
title: Reloading the page rebuilds a running run's view from its recorded events,
  previous agents included
type: fix
---

# ticket-325 — Recharger la page garde l'historique du run en cours

## Objectif

Qu'après un rechargement, la vue d'un run en cours montre toutes ses cartes
(plan, tours précédents, sécurité, revue, validation), et pas seulement
l'agent qui écrit à cet instant.

## Contexte

Capture du 2026-10-02 : ticket-311 au tour 2/3. Après un rechargement, la vue
ne montre plus qu'une carte CODEUR, celle du tour en cours. Le plan, le
tour 1 et le testeur ont disparu.

Au rechargement, l'écran reçoit l'instantané des runs vivants
(`RunRegistry.instantane`) et, à l'abonnement, le tampon du texte en cours
(`JOURNAL_DU_TEXTE`, ticket-185). Les événements déjà passés n'arrivent
jamais. Ils sont pourtant enregistrés en base (`agent_events`), et le
ticket-280 a ajouté `GET /api/v1/runs/{id}/events` pour les relire. Il ne
sert aujourd'hui qu'aux runs terminés (ticket-281).

## Solution proposée

- Le `RunActif` porte l'identifiant en base du run (`db_run_id`), présent
  dans l'instantané.
- Quand l'écran découvre un run vivant par l'instantané, il charge ses
  événements enregistrés, les rejoue dans `applyEvent`, puis applique les
  événements en direct. Il écarte ceux qu'il a déjà, sans doubler le texte
  (comme le ticket-313 pour le rejeu).
- Le plan vérifie le raccord entre l'historique relu et le flux en direct,
  pour qu'aucun événement ne soit perdu ni doublé entre les deux.

## Critères d'acceptation

- [ ] Un test vérifie que l'instantané d'un run vivant porte `db_run_id`
- [ ] Un test du frontend vérifie qu'un run découvert par l'instantané
      déclenche la lecture de ses événements enregistrés
- [ ] Un test vérifie qu'après ce rejeu, la vue montre une carte par passage
      d'agent déjà terminé
- [ ] Un test vérifie qu'un événement reçu à la fois par l'historique et par
      le flux en direct n'apparaît qu'une fois

## Dépendances

Aucune (ticket-280 livré).