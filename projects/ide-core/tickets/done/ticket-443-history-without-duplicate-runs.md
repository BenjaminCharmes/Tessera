---
agent: codeur
created: 2026-10-14
depends_on: []
estimated_days: 0.5
id: ticket-443
pr_number: null
priority: medium
status: done
title: The History list shows one row per ticket run, not the queue run and its child
  twice, and marks interrupted runs
type: fix
---

# ticket-443 — L'Historique sans doublons

## Objectif

Une ligne par run de ticket dans l'onglet Historique, et un run interrompu
reconnaissable comme tel.

## Contexte

Capture du 2026-10-14 : la colonne de l'Historique affiche deux fois
`ticket-430` « En cours… », deux fois `ticket-426`, `ticket-425`,
`ticket-422` ; et des lignes « 0 tour · 925 min » marquées d'un cercle
barré. `GET /api/v1/projects/{id}/runs` (`PipelineRunSummary`) rend à la
fois le run parent d'une file (porté par le premier ticket) et ses runs
enfants, un par ticket (`parent_run_id`). Les « 0 tour » sont des runs
interrompus (veille, redémarrage) restés ouverts des heures.

## Solution proposée

- La liste n'affiche que les runs de ticket : un run qui a des enfants
  (parent d'une file) n'a pas sa propre ligne ; ses enfants en ont une.
  Un run sans parent ni enfant (run d'un seul ticket) reste affiché.
- Un run sans tour terminé et clos par une interruption s'affiche avec la
  pastille « interrompu » (neutre), sans durée aberrante : « — ».
- Le filtrage se fait côté backend (`/projects/{id}/runs` gagne
  `?vue=tickets`, défaut conservé) ou côté frontend — au choix du codeur, en
  le disant dans la PR.

## Critères d'acceptation

- [ ] Un test vérifie qu'une file de deux tickets (un parent, deux enfants)
      donne deux lignes, une par ticket
- [ ] Un test vérifie qu'un run d'un seul ticket, sans parent ni enfant,
      donne une ligne
- [ ] Un test vérifie qu'un run interrompu sans tour affiche « interrompu » et
      « — » à la place de la durée
- [ ] Le tableau « Tous les runs » (ticket-427) applique la même règle

## Dépendances

Aucune.