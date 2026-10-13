---
agent: codeur
created: 2026-10-13
depends_on:
- ticket-416
estimated_days: 1
id: ticket-417
pr_number: 408
priority: high
status: done
title: A Running view lists the project apps alive on the machine, their memory, and
  stops the forgotten ones
type: feat
---

# ticket-417 — Vue « En cours » : les apps qui tournent

## Objectif

Voir d'un coup d'œil quelles apps de projet tournent, ce qu'elles coûtent en
mémoire, et arrêter celles qu'on a oubliées, sans passer projet par projet.

## Contexte

Demande de Benjamin le 2026-10-13. Le ticket-416 expose
`GET /api/v1/services/running` et `POST /api/v1/services/running/{pid}/stop`.
La navigation principale est `components/Sidebar/NavRail.tsx`
(Projets, Tickets, Fichiers, Historique, Agents, Supervision, Statistiques,
Chat).

## Solution proposée

- Une destination « En cours » dans `NavRail.tsx`, placée juste après
  « Projets », avec une pastille du nombre d'apps vivantes (absente à 0).
- `components/EnCoursView/` : en tête, le total de mémoire ; puis une ligne
  par app, groupée par projet : nom du projet et du service, origine
  (« Tessera » / « Lancé à la main »), ports en liens `http://localhost:N`,
  durée depuis le démarrage, mémoire en Mo, bouton « Arrêter ». Tri par
  mémoire décroissante.
- « Arrêter » sur une app `externe` demande une confirmation sur place
  (« Arrêter le processus N ? ») ; sur une app `tessera`, pas de
  confirmation. Après l'arrêt, la liste est relue.
- Relecture toutes les 10 s tant que la vue est visible.
- États vide (« Aucune app de projet ne tourne »), chargement et erreur.
- Couleurs : familles autorisées par ADR-026 uniquement.

## Critères d'acceptation

- [ ] Un test vérifie que `NavRail` affiche « En cours » après « Projets », avec
      une pastille portant le nombre d'apps, absente quand il vaut 0
- [ ] Un test vérifie que la vue affiche chaque app avec son projet, ses ports
      en liens et sa mémoire, triées par mémoire décroissante
- [ ] Un test vérifie que le total de mémoire affiché est la somme des apps
- [ ] Un test vérifie qu'« Arrêter » sur une app externe demande confirmation
      avant d'appeler l'endpoint d'arrêt, et pas sur une app Tessera
- [ ] Un test vérifie l'état vide

## Dépendances

ticket-416.

## Ce que ça ne fait pas

- Ne réorganise pas le reste de la navigation (sujet à part).