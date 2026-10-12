---
agent: codeur
created: 2026-10-12
depends_on:
- ticket-398
estimated_days: 1.5
id: ticket-399
pr_number: 373
priority: high
status: done
title: The Projects tab shows every project as a card in the center view, with search,
  category filter and sorting
type: feat
---

# ticket-399 — L'onglet Projets montre une carte par projet

## Objectif

Naviguer entre les projets sans plisser les yeux sur la barre latérale :
quand l'onglet **Projets** est actif, la zone centrale montre tous les projets
en cartes, que l'on peut chercher, filtrer et trier.

## Contexte

Demande de Benjamin (2026-10-12) : « il est un peu difficile de naviguer entre
[les projets] ». La barre latérale (`Sidebar/ProjectNav.tsx`) les range par
catégorie (`grouperParCategorie`), mais n'affiche qu'un nom. Quand le panneau
`projects` est actif, `CenterView.tsx` montre aujourd'hui la vue du projet
courant (Kanban), qui ne sert à rien pour choisir un projet. Le ticket-398
fournit `GET /api/v1/projects/overview` et l'icône de chaque projet.

## Solution proposée

1. `frontend/src/lib/api.ts` gagne `api.projects.overview()` et
   `api.projects.setCategory(projectId, category)`, ce dernier via la route
   des réglages du ticket-398.
2. Un composant `frontend/src/components/ProjetsView/` est rendu par
   `CenterView.tsx` quand `panel === "projects"`. Il contient :
   - **Une barre d'outils** : un champ de recherche (nom, identifiant,
     description, sans tenir compte de la casse ni des accents), des pastilles
     de catégorie (Toutes, puis une par catégorie, avec leur nombre) et un tri
     (nom, activité récente, création récente).
   - **Une grille de cartes**, regroupée par catégorie sous un titre de
     section quand aucun filtre de catégorie n'est actif, dans l'ordre de
     `grouperParCategorie`. Chaque carte montre :
     - l'icône du projet (`/api/v1/projects/{id}/icon`), ou à défaut un
       carré portant l'initiale du projet ;
     - le nom, l'identifiant et la catégorie ;
     - la description, sur 3 lignes au plus ;
     - le lien du dépôt (`lienDuDepot`), qui s'ouvre dans un nouvel onglet
       sans sélectionner le projet ;
     - la date de création et l'activité récente en relatif (« il y a 2 j »),
       avec la date exacte en info-bulle ;
     - les compteurs de tickets (à faire, en cours, bloqués, faits) ;
     - un point animé si un run tourne.

     Un clic sur la carte, ou Entrée quand elle a le focus, sélectionne le
     projet comme la barre latérale. La carte du projet actif est marquée
     d'une barre `violet` (ADR-026 : jamais en couleur de texte).
   - **Un menu par carte** pour changer de catégorie : choisir une catégorie
     existante, en saisir une nouvelle ou la retirer. La liste est ensuite
     rechargée, et la barre latérale suit.
   - **Les états** : chargement (squelette), erreur (message et bouton
     « Réessayer »), aucun résultat (message et bouton « Effacer la
     recherche »).
3. La recherche, le filtre et le tri survivent au changement d'onglet, comme
   les filtres du Kanban.

## Critères d'acceptation

- [ ] Un test de `frontend/src/components/ProjetsView/ProjetsView.test.tsx` vérifie qu'avec trois projets dans deux catégories, la vue affiche trois cartes sous deux titres de section
- [ ] Un test de `frontend/src/components/ProjetsView/ProjetsView.test.tsx` vérifie que la recherche « deminéur » (casse et accents différents) ne garde que la carte du projet `demineur`
- [ ] Un test de `frontend/src/components/ProjetsView/ProjetsView.test.tsx` vérifie qu'un clic sur la pastille d'une catégorie ne garde que ses projets, et que la pastille affiche leur nombre
- [ ] Un test de `frontend/src/components/ProjetsView/ProjetsView.test.tsx` vérifie que le tri « activité récente » place en premier le projet dont `last_activity` est la plus récente
- [ ] Un test de `frontend/src/components/ProjetsView/ProjetsView.test.tsx` vérifie qu'un clic sur une carte appelle `onSelectProject` avec ce projet, et qu'un clic sur le lien du dépôt ne l'appelle pas
- [ ] Un test de `frontend/src/components/ProjetsView/ProjetsView.test.tsx` vérifie qu'une carte sans icône affiche l'initiale du projet
- [ ] Un test de `frontend/src/components/ProjetsView/ProjetsView.test.tsx` vérifie que choisir une autre catégorie dans le menu d'une carte appelle `api.projects.setCategory` puis recharge la vue d'ensemble
- [ ] Un test de `frontend/src/components/CenterView.test.tsx` vérifie que `panel="projects"` rend `ProjetsView`

## Dépendances

ticket-398 (l'endpoint de vue d'ensemble, l'icône et l'écriture de la
catégorie).

## Estimation

1,5 jour.

## Risques

Les couleurs suivent ADR-026 (états en zinc, red, amber, green ou blue ;
violet réservé à l'identité et à l'interaction). Un test verrouille ces
règles : à respecter dès l'écriture.

## Ce que ça ne fait pas

- Ne remplace pas la liste de la barre latérale, qui reste la navigation
  rapide.
- Ne permet ni de réordonner les catégories ni de créer des projets depuis la
  vue (la modale « Nouveau projet » reste dans la barre latérale).