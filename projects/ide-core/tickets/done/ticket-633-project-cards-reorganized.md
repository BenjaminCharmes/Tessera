---
id: ticket-633
title: "Project cards keep their footer aligned, name their two launches, and launch one ticket on worktree projects"
type: fix
status: done
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-10-28
---

# ticket-633 — Des cartes de projet alignées, et un lancement possible partout

## Objectif
Que les cartes de la vue Projets s'alignent entre elles, disent ce que lance
chaque bouton, et ne proposent rien que le backend refuse.

## Contexte
Retours du 28/10 :
- la rangée d'actions n'existait que sur certaines cartes : dates et compteurs
  remontaient d'une carte à l'autre ;
- deux « Lancer » se confondaient : l'app (services) et la file de tickets ;
- sur un projet à worktree (Kadoomi, Devinoo), « File » échouait toujours en 422 :
  un tel projet ne tourne qu'un ticket à la fois (ADR-056), et la vue d'ensemble
  ne le disait pas ;
- un message d'erreur ou une confirmation poussait la carte.

## Solution proposée
- La vue d'ensemble expose `worktree` (`project_overview.py`, lu par `PolitiqueRun`).
- Le pied de carte a une ligne de dates, puis une ligne de hauteur fixe : les
  compteurs à gauche (« À faire » toujours, les autres s'ils ne sont pas nuls),
  les actions à droite.
- « Lancer l'app » / « Arrêter l'app » pour les services ; « File (n) » pour la
  file ; « Ticket suivant » sur un projet à worktree, qui lance le premier ticket
  à faire en mode `single`. « Mettre en ligne » devient une icône.
- Confirmations et messages s'ouvrent en bulle au-dessus de leur bouton.
- `ProjectOverview` et `TicketCounts` passent dans `types/apercuProjet.ts` :
  `types/api.ts` touchait son plafond de longueur.

## Critères d'acceptation
- [x] Un test du backend vérifie que `worktree` vaut vrai pour un projet `tracked` qui déclare `worktree`, et faux sinon
- [x] Un test de `LancerFile` vérifie qu'un projet à worktree n'offre pas « File » et lance le premier ticket à faire en mode `single`
- [x] Un test de `ProjetCarte` vérifie que les actions sont sur la ligne des compteurs, de hauteur fixe
- [x] Les boutons de services s'appellent « Lancer l'app » et « Arrêter l'app »
- [x] Le lien du dépôt vit dans le pied, sur une ligne gardée même sans dépôt
- [x] Captures à 1536 relues : lien, dates, compteurs et boutons alignés d'une carte à l'autre, avec ou sans bouton

## Ce que ça ne fait pas
- Ne lève pas la règle d'un ticket à la fois sur les projets à worktree.
- Le champ `worktree` n'arrive dans l'interface qu'après un redémarrage du backend.
