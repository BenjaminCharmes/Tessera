---
agent: codeur
created: 2026-10-12
depends_on: []
estimated_days: 1
id: ticket-398
pr_number: null
priority: high
status: done
title: A project overview endpoint serves everything the project cards show, and a
  project's category can be changed from the API
type: feat
---

# ticket-398 — Un endpoint de vue d'ensemble pour les cartes de projets

## Objectif

Fournir en **une seule requête** tout ce que la vue « Projets » (ticket-399)
affiche pour chaque projet, et permettre de changer la catégorie d'un projet
depuis l'interface.

## Contexte

Quatorze projets à ce jour, et le nombre augmente : la barre latérale ne
montre qu'un nom, rangé par catégorie (ticket-175, catégories déclarées le
2026-10-12). Benjamin veut voir dans la zone centrale une carte par projet,
avec sa date de création, sa description, le lien du dépôt et son activité.

Une requête par projet et par information ferait des dizaines d'appels :
c'est le défaut corrigé par les tickets 364 à 367 pour les PR. Tout part donc
d'un seul endpoint, mis en cache.

## Solution proposée

1. `GET /api/v1/projects/overview` rend, pour chaque projet listé par
   `ProjectLoader.list_projects()`, un `ProjectOverview` :
   - `id`, `name`, `category`, `description` et `github_remote`, déjà connus
     du `Project` ;
   - `created_at` : date du premier commit qui touche le dossier du projet
     (`git log --diff-filter=A --format=%cI -- .`, le plus ancien), sinon date
     de création du dossier ;
   - `last_activity` : date du dernier commit du dossier du projet, sinon
     `null` ;
   - `tickets` : nombre de fiches par statut (`todo`, `in_progress`,
     `in_review`, `blocked`, `done`), lu depuis les dossiers de tickets ;
   - `run_actif` : un run est ouvert sur le projet (`RUN_REGISTRY`) ;
   - `icon` : `true` si une icône d'app est trouvée (point 2).

   Le calcul git et le comptage sont mis en cache par projet. Le cache est
   invalidé quand la date de modification de `.git/HEAD`, de
   `.git/refs/heads/` ou du dossier `tickets/` change. Deux appels de suite
   ne relancent aucune commande git.
2. `GET /api/v1/projects/{project_id}/icon` sert la première icône trouvée
   parmi `frontend/public/favicon.svg`, `frontend/public/favicon.png`,
   `frontend/public/icon.svg`, `frontend/public/icons/icon-192.png`,
   `public/favicon.svg` et `public/favicon.png`, avec le bon `Content-Type`.
   Sans icône, il renvoie 404. Le chemin est toujours l'un de ces chemins
   fixes, sous le dossier du projet : jamais un chemin reçu de la requête.
3. Le corps de la mise à jour des réglages d'un projet (la route qui écrit
   `autonomy` et `merge_without_ci` à la racine d'`agents.json`) accepte
   `category`. Elle écrit à la racine du manifeste ; une chaîne vide retire la
   catégorie. Le refus pendant un run reste inchangé.

## Critères d'acceptation

- [ ] Un test de `backend/tests/test_projects_overview.py` vérifie que `GET /api/v1/projects/overview` rend, pour un projet dans un vrai dépôt git temporaire, `created_at` égal à la date du premier commit qui touche son dossier, et `last_activity` égal à celle du dernier
- [ ] Un test de `backend/tests/test_projects_overview.py` vérifie que les compteurs de `tickets` reflètent les fiches présentes dans `todo/`, `in-progress/` et `done/`
- [ ] Un test de `backend/tests/test_projects_overview.py` vérifie qu'un second appel sans changement dans le dépôt ne lance aucune commande git (sous-processus simulé, compteur d'appels)
- [ ] Un test de `backend/tests/test_projects_overview.py` vérifie que `GET /api/v1/projects/{id}/icon` sert `frontend/public/favicon.svg` avec `Content-Type: image/svg+xml`, et renvoie 404 pour un projet sans icône
- [ ] Un test de `backend/tests/test_projects_overview.py` vérifie que la mise à jour des réglages avec `category` écrit la catégorie à la racine d'`agents.json`, et qu'une chaîne vide la retire
- [ ] Un test de `backend/tests/test_projects_overview.py` vérifie qu'un projet sans dépôt git apparaît quand même dans la vue d'ensemble, avec `last_activity` à `null`

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

Pour ide-core (`git_root: ancestor`), les dates doivent porter sur le dossier
du projet et non sur tout le dépôt : c'est pourquoi on utilise `-- .` depuis
ce dossier.

## Ce que ça ne fait pas

- Ne crée aucune icône : il sert seulement celle que le projet a déjà.
- Ne change pas la liste des projets de la barre latérale.