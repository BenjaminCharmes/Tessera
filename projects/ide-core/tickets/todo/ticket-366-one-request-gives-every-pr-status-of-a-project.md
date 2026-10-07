---
id: ticket-366
title: "One request gives the status of every PR of a project"
type: feat
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: ["ticket-370"]
estimated_days: 1
created: 2026-10-07
---

# ticket-366 — Une requête donne l'état de toutes les PR d'un projet

## Objectif

Que le coût d'ouverture d'un projet ne grandisse plus avec le nombre de
tickets livrés : un seul appel donne l'état de toutes ses PR, et GitHub n'est
interrogé que pour ce qui peut encore changer.

## Contexte

Chaque carte de ticket appelle aujourd'hui
`GET /projects/{id}/tickets/{ticket_id}/pr-status`. Le ticket-364 a rendu ces
appels rapides (cache `backend/src/tessera/services/pr_status_cache.py` :
PR réglées en base, PR ouvertes 30 s en mémoire), mais leur **nombre** suit
celui des tickets : 139 sur ide-core le 2026-10-07, après quelques semaines,
et autant de connexions qui occupent les six slots du navigateur.

Une PR qui n'est pas encore en base coûte en plus deux appels GitHub à elle
seule, alors que GitHub sait lister toutes les PR d'un dépôt par pages de 100.

## Solution proposée

Nouvel endpoint `GET /projects/{project_id}/pr-statuses`
(`backend/src/tessera/routers/tickets.py` ou un routeur voisin), qui rend une
entrée par ticket portant un `pr_number` :
`{ticket_id, pr_number, state, ci_status, pr_url}`.

1. Les PR `merged` ou `closed` déjà dans la table `pr_status_cache` sont
   rendues sans appel GitHub.
2. Les PR absentes de la table sont cherchées par **un** listing paginé
   `GET /repos/{repo}/pulls?state=all&per_page=100`, en s'arrêtant dès que
   toutes ont été trouvées ou que les pages sont épuisées. Celles qui sont
   réglées sont écrites dans la table.
3. Pour les PR `open`, le statut de CI vient des check-runs, avec le cache
   mémoire de 30 s du ticket-364.
4. Un `pr_number` introuvable dans le dépôt (hérité d'un autre dépôt,
   ticket-217) est omis de la réponse, sans erreur.

L'authentification `STATIC_TOKEN` est globale (`StaticTokenMiddleware`,
`backend/src/tessera/main.py`) : l'endpoint n'a rien à y ajouter. Le
`project_id` est validé pour toutes les routes par le ticket-370, dont ce
ticket dépend : l'endpoint passe par le même mécanisme.

L'endpoint par ticket existant reste en place : rien d'autre ne change.
`github_workflow.py` et `GitHubService.get_pull_request_status` ne sont pas
modifiés.

## Critères d'acceptation

- [ ] Un test de `backend/tests/test_pr_statuses.py` montre que, pour trois tickets dont les PR mergées sont déjà en base, `GET /projects/{id}/pr-statuses` rend trois entrées sans aucun appel GitHub
- [ ] Un test de `backend/tests/test_pr_statuses.py` montre que trois PR absentes de la base sont obtenues par un seul appel de listing GitHub, et que les réglées sont ensuite écrites en base
- [ ] Un test de `backend/tests/test_pr_statuses.py` montre que la CI d'une PR ouverte n'est demandée qu'une fois par période de 30 secondes (horloge simulée)
- [ ] Un test de `backend/tests/test_pr_statuses.py` montre qu'un `pr_number` absent du listing est omis de la réponse, avec un code 200
- [ ] Un test de `backend/tests/test_pr_statuses.py` montre qu'un ticket sans `pr_number` n'apparaît pas dans la réponse
- [ ] Le diff ne modifie ni `backend/src/tessera/services/github_workflow.py` ni la méthode `get_pull_request_status` de `backend/src/tessera/services/github_service.py`

## Dépendances

ticket-370 (validation du `project_id` sur toutes les routes). Un premier run,
le 2026-10-07, a été bloqué par l'audit sécurité sur ce point et sur une
authentification jugée absente, qui est en fait globale.

## Estimation

1 jour.

## Risques

Un dépôt de plusieurs milliers de PR demanderait plusieurs pages la première
fois ; ensuite, seules les PR nouvelles ou ouvertes coûtent un appel.

## Ce que ça ne fait pas

- Ne change pas le frontend : le ticket-367 branche les cartes sur cet
  endpoint.
- Ne supprime pas l'endpoint par ticket.
