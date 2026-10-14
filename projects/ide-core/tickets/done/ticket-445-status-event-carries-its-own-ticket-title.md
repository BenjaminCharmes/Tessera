---
agent: codeur
created: 2026-10-14
depends_on: []
estimated_days: 0.5
id: ticket-445
pr_number: null
priority: medium
status: done
title: A ticket status event in a queue always carries the title of its own ticket,
  never the previous one's
type: fix
---

# ticket-445 — Un évènement de statut porte le titre de son propre ticket

## Objectif

Que l'évènement `ticket_status_changed` d'un ticket, dans une file, porte le
titre de ce ticket et non celui du ticket précédent.

## Contexte

Signalé par la session affût le 2026-10-14 (arrivé par `/signalements`, en
attente puis écrit à la fin d'un run, ticket-430) : file 070-074 coupée par
la limite de session ; l'évènement `ticket_status_changed` du ticket-073
portait `ticket_titre` « Backend: research lists the extras a candidate
needs and its full cost », le titre du ticket-070. La première moitié du
signalement (ticket coupé compté parmi les faits) est traitée par le
ticket-444.

Cause probable, `services/run_executor.py` (`envoyer`) : le titre n'est
relu (`titre_getter`) que si **cet** évènement fait changer
`run.ticket_id` (`run.ticket_id != ancien_ticket_id`). Quand un autre type
d'évènement a déjà fait basculer le run sur le ticket suivant, le
`ticket_status_changed` qui suit trouve l'id inchangé et garde
`run.ticket_titre`, celui de l'ancien ticket.

## Solution proposée

- Mémoriser le ticket auquel le titre en cache se rapporte (par exemple
  `run.ticket_titre_de`), et relire le titre dès que `run.ticket_id` en
  diffère, quel que soit l'évènement qui a provoqué le changement.

## Critères d'acceptation

- [ ] Un test vérifie que, dans une file, après un évènement non-statut qui
      fait passer le run au ticket B, le `ticket_status_changed` suivant porte
      le titre de B
- [ ] Un test vérifie que le titre n'est relu sur disque qu'une fois par
      ticket (pas à chaque évènement)
- [ ] Les tests existants du ticket-324 restent verts

## Dépendances

Aucune.