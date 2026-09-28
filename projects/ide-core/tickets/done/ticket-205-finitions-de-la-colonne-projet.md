---
id: ticket-205
title: "Sidebar polish: PR number after delivery, project removal, long names"
type: fix
status: done
pr_number: 78
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-28
---

# ticket-205 — Finitions de la colonne projet

## Objectif
Corriger trois défauts relevés à l'usage dans la colonne de gauche : un
bouton « Ouvrir une PR » sur des tickets déjà mergés, un « Retirer ce projet »
introuvable, et un nom de projet long qui passe sous les boutons de l'en-tête.

## Contexte
- **PR** : `LivraisonService` ouvre et merge la PR, mais personne n'écrit son
  numéro dans le ticket. Les vingt tickets `done` de démineur ont leurs PR
  mergées sur GitHub et `pr_number: null` sur disque — la carte en conclut
  qu'il n'y a pas de PR et propose d'en ouvrir une. Ce bouton appelait
  `create-pr`, qui ne pousse rien, avec la branche `ticket-XXX` pré-remplie
  alors que les runs créent `ticket-XXX-<slug>` ; son échec était avalé sans
  message. Le panneau d'activité du ticket porte déjà le bon geste — « Pousser
  et ouvrir la PR » (ticket-081).
- **Retrait** : l'action existe (ticket-063), au pied du panneau « Git ».
  Rien ne l'y annonce.
- **Nom long** : le `<button>` du sélecteur prend la largeur de son contenu,
  pas celle de son conteneur ; le `truncate` ne coupe donc jamais.

## Solution proposée
- Après une livraison qui a ouvert une PR, le routeur de l'orchestrateur écrit
  `pr_number` dans le ticket et commite le suivi (`chore: tessera pipeline
  bookkeeping`) pour que l'arbre reste propre (ADR-018). Un échec de cette
  écriture ne fait pas échouer la livraison (ADR-030).
- La carte perd son bouton et son formulaire de PR ; le badge `PR #N` reste.
- « Retirer ce projet de l'IDE… » passe du panneau Git au menu du sélecteur
  de projet.
- Le bouton du sélecteur est borné à la largeur de son conteneur.
- Le bouton « Pipeline » reçoit un chevron : un libellé gris seul ne se
  lisait pas comme cliquable.

## Critères d'acceptation
- [x] Un test vérifie qu'une livraison qui rend `pr_number` l'écrit dans le frontmatter du ticket
- [x] Un test vérifie qu'après cette écriture, sur un projet `tracked`, `git status --porcelain --untracked-files=no` est vide
- [x] Un test vérifie qu'après ce commit, la base du run avance
- [x] Un test vérifie qu'une exception pendant cette écriture laisse la `Livraison` inchangée
- [x] `TicketCard` n'affiche plus de bouton « Ouvrir une PR », quel que soit le statut
- [x] Le menu du sélecteur de projet porte « Retirer ce projet de l'IDE… », qui ouvre `RemoveProjectModal`
- [x] `GitLinkPanel` ne porte plus ce bouton
- [x] Le bouton du sélecteur porte `max-w-full`, verrouillé par un test
- [x] Le bouton « Pipeline » porte un chevron qui suit son état ouvert/fermé
- [x] `uv run pytest`, `npm run test`, `npm run build` passent

## Ce que ça ne fait pas
- Ne renseigne pas `pr_number` des tickets livrés avant ce correctif.
- Sur un dépôt qui versionne ses tickets, le numéro est commité sur la
  branche du ticket, puis la base du run avance : il atteint la branche
  distante avec la PR du ticket **suivant**, pas avec la sienne, déjà
  mergée.
- L'endpoint `create-pr` reste côté backend ; seul son appel par la carte
  disparaît.

## Dépendances
Aucune.

## Estimation
Une journée.

## Risques
Commiter après la livraison : sur un run où la livraison s'est arrêtée à
mi-chemin, le commit de suivi part sur la branche active — celle du ticket.
