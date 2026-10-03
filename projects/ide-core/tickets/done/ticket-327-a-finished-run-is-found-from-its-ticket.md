---
agent: codeur
created: 2026-10-02
depends_on: []
estimated_days: 1
id: ticket-327
plan: true
pr_number: null
priority: medium
status: done
title: A finished run is reopened from its ticket and from Supervision, opens complete,
  and the stats view loads fast
type: feat
---

# ticket-327 — Un run terminé se rouvre depuis son ticket

## Objectif

Qu'on retrouve le déroulé d'un ticket là où on le cherche, et qu'il s'ouvre
vite et complet.

## Contexte

Le ticket-281 rouvre un run terminé, avec toutes ses cartes. Vérifié le
2026-10-02 sur le ticket-316 : plan, deux tours de codeur, sécurité,
reviewer, validateur avec ses critères. Mais :

- **on ne le trouve pas** : la seule entrée est le tableau des derniers runs,
  tout en bas de la vue Statistiques. L'utilisateur a demandé si la
  fonction existait ;
- **la vue Statistiques met de 35 à 90 secondes à charger** quand des runs
  tournent (`GET /api/v1/usage/stats`, `services/usage_stats.py`). Elle reste
  sur « Chargement… » ;
- **le résumé du run rouvert est faux** : il affiche « Revue terminée —
  livraison en cours » et un « Ticket : » vide, alors que le run est
  terminé. Les événements relus d'un ticket joué dans une file ne
  contiennent ni `run_closed` ni le numéro du ticket.

## Solution proposée

- Le panneau d'un ticket (Voir le ticket) et la carte d'un run clos dans la
  Supervision proposent « Revoir le run », qui ouvre la même vue que le
  ticket-281, sur le dernier run de ce ticket.
- Un endpoint léger rend les runs d'un ticket (`GET /projects/{id}/tickets/{ticket_id}/runs`),
  sans calculer les statistiques.
- Le plan mesure ce qui ralentit `usage_stats` et le corrige (index, requête
  bornée), avec une cible : moins de 2 secondes sur la base actuelle.
- La vue rouverte affiche le numéro du ticket, et « Run terminé » quand le run
  est clos, même pour un ticket joué dans une file.

## Critères d'acceptation

- [ ] Un test vérifie que `GET /projects/{id}/tickets/{ticket_id}/runs` rend
      les runs de ce ticket, du plus récent au plus ancien
- [ ] Un test du frontend vérifie que le panneau d'un ticket qui a un run
      terminé affiche « Revoir le run » et ouvre la vue du ticket-281
- [ ] Un test du frontend vérifie que la carte d'un run clos dans la
      Supervision propose « Revoir le run »
- [ ] Un test vérifie que la vue rouverte d'un ticket joué dans une file
      affiche son numéro et « Run terminé »
- [ ] Un test mesure `usage_stats` sur une base de 50 000 événements et
      vérifie qu'il répond en moins de 2 secondes

## Dépendances

Aucune (tickets 280 et 281 livrés).