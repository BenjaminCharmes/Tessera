---
id: ticket-332
title: "A selected ticket lists its finished runs and offers to replay each one"
type: fix
status: done
pr_number: 248
priority: medium
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-05
---

# ticket-332 — Un ticket sélectionné propose de revoir ses runs terminés

## Objectif

Qu'on puisse rouvrir le déroulé d'un run terminé depuis le ticket lui-même,
sans passer par le bas de la vue Statistiques.

## Contexte

Le ticket-327 devait proposer « Revoir le run » depuis le panneau d'un ticket.
Le 2026-10-05, l'utilisateur ne l'a trouvé nulle part. Le bouton a été ajouté
à `TicketActivity`, mais ce bloc n'est plus rendu que dans le panneau latéral
de la Supervision : la colonne de droite qui le montrait à côté d'un ticket a
disparu au ticket-223. Le client `api.tickets.runs`
(`GET /projects/{id}/tickets/{ticket_id}/runs`), livré par le 327, n'est
appelé par aucun écran.

Le test du 327 vérifiait le composant isolé, pas sa présence dans un écran :
il passait sur une fonction invisible.

Côté Supervision, le bouton n'apparaît que pour les runs gardés en mémoire
par le backend depuis son démarrage ; après un redémarrage, elle est vide.

## Solution proposée

Quand le centre affiche le fichier d'un ticket (clic sur un ticket du tableau
ou de la liste), une bande sous l'en-tête liste ses runs terminés, lus par
`api.tickets.runs` : statut, date, tours, coût, et « Revoir le run ». Le
bouton remplace le fichier par la vue en lecture seule du ticket-281
(`RunHistorique`) ; la fermer ramène au ticket. Un ticket sans run terminé
n'affiche pas de bande. Un fichier ouvert depuis l'arbre non plus.

## Critères d'acceptation

- [x] Un test du frontend rend l'éditeur sur un ticket qui a un run terminé et
      vérifie qu'il affiche « Revoir le run »
- [x] Le même test clique sur le bouton et vérifie que la vue du run
      (`RunHistorique`) remplace le fichier du ticket, puis que la fermer
      ramène au ticket
- [x] Un test vérifie qu'un run non terminé (enveloppe de file, run en cours)
      n'est pas proposé
- [x] Un test vérifie qu'un fichier ouvert depuis l'arbre n'affiche pas la
      bande

## Ce que ça ne fait pas

La Supervision continue de ne lister que les runs vivants du backend : elle
reste l'écran du présent. Le passé se retrouve depuis le ticket, ou depuis la
vue Statistiques.

## Dépendances

Aucune.

## Estimation

0,5 jour.
