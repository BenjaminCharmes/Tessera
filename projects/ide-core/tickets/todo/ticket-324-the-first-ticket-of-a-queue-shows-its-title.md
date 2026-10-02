---
id: ticket-324
title: "The first ticket of a queue shows its title to a screen that was already open"
type: fix
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-02
---

# ticket-324 — Le premier ticket d'une file affiche son titre

## Objectif

Qu'un écran déjà ouvert affiche le titre du ticket en cours, quel que soit le
rang de ce ticket dans la file.

## Contexte

Capture du 2026-10-02, dans la Supervision : la carte d'ide-core (file 3/4)
affiche le titre de son ticket, celle de `carriere` (file 1/2) non. Pourtant,
l'instantané de la WebSocket porte bien le titre des deux.

`run_executor.emetteur` (vers les lignes 68-83) ne joint `ticket_titre` à un
événement `ticket_status_changed` que lorsque `run.ticket_id` **change**.
Depuis le ticket-286, une file connaît son premier ticket et son titre dès la
création du `RunActif` : le premier `ticket_status_changed` ne compte donc pas
comme un changement, et il part sans titre. Un écran ouvert avant le
démarrage de la file ne reçoit que des événements, jamais l'instantané : il
n'apprend le titre du premier ticket qu'en rechargeant la page.

## Solution proposée

Tout événement `ticket_status_changed` porte `ticket_titre` dès que le run le
connaît. Le titre n'est relu sur disque que lorsque le ticket change.

## Critères d'acceptation

- [ ] Un test vérifie que le premier `ticket_status_changed` d'une file porte
      `ticket_titre`
- [ ] Un test vérifie que le titre n'est relu sur disque qu'une fois par
      ticket (le lecteur de titre est remplacé par une doublure qui compte
      ses appels)
- [ ] Un test du frontend vérifie qu'une carte de run créée par un événement,
      sans instantané, affiche le titre reçu

## Dépendances

Aucune.
