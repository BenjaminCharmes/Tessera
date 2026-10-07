---
agent: codeur
created: 2026-10-07
depends_on: []
estimated_days: 0.5
id: ticket-364
pr_number: null
priority: high
status: done
title: A PR's status is remembered instead of being asked of GitHub on every card
type: fix
---

# ticket-364 — L'état d'une PR se retient au lieu d'être redemandé à GitHub

## Objectif

Ouvrir un projet ne doit plus déclencher un appel GitHub par carte de ticket :
l'état d'une PR mergée ou fermée ne change plus, il se retient.

## Contexte

Chaque carte de ticket qui porte un `pr_number` appelle
`GET /projects/{id}/tickets/{ticket_id}/pr-status`
(`backend/src/tessera/routers/tickets.py`). L'endpoint interroge GitHub deux
fois par appel (la PR, puis ses check-runs) via
`GitHubService.get_pull_request_status`, sans aucun cache : environ une
seconde par carte.

Mesuré le 2026-10-07 : ide-core a 139 tickets avec un `pr_number`. Ouvrir le
projet lance 139 appels ; le navigateur n'ouvre que six connexions vers le
backend, donc les requêtes des autres onglets (Statistiques, Supervision)
attendent derrière, jusqu'à 5,5 s. Chaque ouverture consomme environ
280 appels du quota GitHub (5 000 par heure). Le nombre de cartes concernées
grandit à chaque ticket livré.

## Solution proposée

Un module `backend/src/tessera/services/pr_status_cache.py` utilisé par
l'endpoint `pr-status` uniquement :

1. Une PR à l'état `merged` ou `closed` est définitive : son statut
   (`state`, `ci_status`, `pr_url`) est écrit dans une table SQLite
   `pr_status_cache`, clé `(repo, pr_number)`, et relu de là ensuite — y
   compris après un redémarrage du backend.
2. Une PR `open` est gardée en mémoire 30 secondes, puis redemandée.
3. Les 404 et les erreurs restent traités comme aujourd'hui : rien n'est mis
   en cache dans ce cas.

La table s'ajoute par une migration **en fin** de `_MIGRATIONS`
(`backend/src/tessera/services/database.py`).

`GitHubService.get_pull_request_status` et `github_workflow.py` ne changent
pas : la livraison attend la CI avec eux et doit toujours lire l'état réel.

## Critères d'acceptation

- [ ] `backend/src/tessera/services/database.py` crée la table `pr_status_cache` par une nouvelle migration ajoutée en fin de `_MIGRATIONS`
- [ ] Un test de `backend/tests/test_pr_status_cache.py` montre que deux appels de l'endpoint `pr-status` pour une PR mergée n'appellent GitHub qu'une fois
- [ ] Un test de `backend/tests/test_pr_status_cache.py` montre qu'une PR mergée déjà enregistrée en base est rendue sans appel GitHub après que le cache mémoire a été vidé
- [ ] Un test de `backend/tests/test_pr_status_cache.py` montre qu'une PR ouverte est redemandée à GitHub une fois les 30 secondes écoulées (horloge simulée), et pas avant
- [ ] Un test de `backend/tests/test_pr_status_cache.py` montre qu'un 404 de GitHub n'est pas mis en cache
- [ ] Le diff ne modifie ni `backend/src/tessera/services/github_workflow.py` ni la méthode `get_pull_request_status` de `backend/src/tessera/services/github_service.py`

## Dépendances

Aucune.

## Estimation

0,5 jour.

## Risques

Une PR rouverte après fermeture garderait l'état `closed` en cache. C'est
rare, et le lien de la carte mène toujours à la PR réelle.

## Ce que ça ne fait pas

- Ne change pas le frontend : la carte appelle toujours l'endpoint, qui
  répond désormais sans GitHub (ticket-365 pour le retour de fenêtre).
- Pas d'endpoint groupé par projet.