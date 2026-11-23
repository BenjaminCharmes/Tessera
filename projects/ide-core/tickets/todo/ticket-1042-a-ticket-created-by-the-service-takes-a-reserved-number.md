---
id: ticket-1042
title: "A ticket created by the service takes its number through the reservation"
type: fix
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-11-23
---

# ticket-1042 — Un ticket créé par le service prend son numéro par la réservation

## Objectif

Qu'un ticket créé par Tessera lui-même (signalement d'un agent, création depuis
l'interface) ne prenne jamais un numéro déjà réservé par
`scripts/prochain_numero.py`.

## Contexte

Le 23/11, `prochain_numero.py` a réservé 1040 pour une fiche écrite à la main
dans un worktree, poussée sur une branche `chore-…`. Quelques minutes plus
tard, un signalement du codeur d'un autre projet a créé
`tickets/todo/ticket-1040-…` dans le checkout d'ide-core : deux fiches, un
numéro. La fiche manuelle a dû être renumérotée.

La cause est dans le code :

- `reserver` (`backend/src/tessera/services/noyau/numerotation.py`) lit
  l'arbre, `origin/<base>`, les branches `origin/ticket-*` et le fichier de
  réservation, puis écrit le numéro rendu : il n'est jamais rendu deux fois ;
- `TicketService._next_id`
  (`backend/src/tessera/services/projets/ticket_service.py`) rend
  `highest_number(arbre) + 1` : ni réservation, ni base, ni branches ;
- un signalement (`routers/signalements.py`,
  `services/pipeline/signalements_en_attente.py`) construit un ticket sans
  identifiant et passe par `create_ticket` ou `create_ticket_sync`, donc
  par `_next_id`.

## Solution proposée

`TicketService._next_id` prend son numéro par `reserver`, avec le dossier
d'état des réglages, et garde le format d'identifiant actuel. Un dossier de
projet sans dépôt git lisible garde le comportement d'aujourd'hui
(`numeros_pris` répond alors par l'arbre seul). `github_sync` a sa propre
numérotation et n'est pas touché.

## Critères d'acceptation

- [ ] Un test réserve un numéro N par `reserver` pour un projet dont l'arbre
      s'arrête à N-1, puis crée un ticket sans identifiant par
      `TicketService.create_ticket_sync` : le ticket porte N+1.
- [ ] Un test crée deux tickets sans identifiant à la suite : deux numéros
      différents, et le fichier de réservation porte le second.
- [ ] Un test crée un ticket sans identifiant dans un dossier hors de tout
      dépôt git : il porte le plus grand numéro de l'arbre plus un.
- [ ] Un test de signalement (`tests/test_signalements.py`) vérifie qu'un
      signalement écrit après une réservation ne reprend pas le numéro réservé.

## Ce que ça ne fait pas

- Ne renumérote aucune fiche existante.
- Ne touche pas à la numérotation de `github_sync`.
- Ne fait pas compter les branches distantes hors `origin/ticket-*` : la
  réservation suffit à les couvrir.

## Dépendances

Aucune.

## Estimation

Une demi-journée.

## Risques

Les tests qui créent des tickets écrivent désormais un fichier de réservation :
ils doivent viser un dossier d'état jetable, pas celui de la machine.
