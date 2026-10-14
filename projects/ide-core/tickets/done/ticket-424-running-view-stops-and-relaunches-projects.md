---
agent: codeur
created: 2026-10-13
depends_on: []
estimated_days: 1
id: ticket-424
pr_number: 418
priority: medium
status: done
title: The Running view stops a whole project at once, shows a spinner until it is
  gone, and can relaunch it
type: feat
---

# ticket-424 — Vue « En cours » : arrêter un projet entier, attendre, relancer

## Objectif

Arrêter un projet d'un clic (back et front ensemble), voir que l'arrêt est
en cours sans pouvoir recliquer, et pouvoir le relancer depuis la même vue.

## Contexte

Retour de Benjamin le 2026-10-13 sur la vue livrée par le ticket-417
(`frontend/src/components/EnCoursView/`) :

- il faut arrêter séparément le backend et le frontend d'un même projet ;
- après « Arrêter », rien n'indique que l'arrêt est en cours : le bouton
  reste cliquable jusqu'à ce que l'app disparaisse de la liste (relecture
  toutes les 10 s) ;
- une app arrêtée disparaît : impossible de la relancer d'ici.

Endpoints existants : `GET /api/v1/services/running`,
`POST /api/v1/services/running/{pid}/stop` (ticket-416),
`POST /api/v1/projects/{id}/services/start` et `…/stop` (ticket-138),
`GET /api/v1/projects/overview` (porte `services_declares` et
`services_en_cours`, ticket-410).

## Solution proposée

- **Arrêter le projet** : un bouton dans l'en-tête de chaque groupe de
  projet. Il arrête toutes les apps du groupe : `…/services/stop` pour les
  apps `tessera`, puis `…/running/{pid}/stop` pour chaque app `externe`,
  après **une seule** confirmation qui liste les pids externes concernés.
  Le bouton par app reste disponible.
- **Arrêt en cours** : dès le clic, la ligne (ou le groupe) passe en état
  « Arrêt… » avec un indicateur animé, boutons désactivés ; la relecture
  passe à 2 s tant qu'un arrêt est en attente ; l'état se lève quand le pid
  a disparu de l'inventaire. Au-delà de 30 s : message d'erreur, boutons
  réactivés.
- **Relancer** : une section « Arrêtés » sous la liste, qui montre les
  projets dont `services_declares` est vrai et qui n'ont plus aucune app
  dans l'inventaire, avec un bouton « Lancer » (`…/services/start`) qui
  passe aussi par un état « Lancement… » jusqu'à ce que le projet
  réapparaisse dans l'inventaire (même délai de 30 s). Section repliée par
  défaut s'il y a plus de 5 projets.

## Critères d'acceptation

- [ ] Un test vérifie que « Arrêter le projet » appelle `services/stop` du
      projet et l'arrêt par pid de chaque app externe du groupe, après une
      seule confirmation quand il y a une app externe
- [ ] Un test vérifie qu'après un clic sur « Arrêter », le bouton est
      désactivé et un indicateur « Arrêt… » est affiché tant que le pid est
      encore dans l'inventaire
- [ ] Un test (faux minuteur) vérifie qu'au-delà de 30 s sans disparition,
      un message d'erreur s'affiche et le bouton est réactivé
- [ ] Un test vérifie que la section « Arrêtés » liste un projet qui déclare
      des services sans en avoir aucun dans l'inventaire, avec « Lancer »
- [ ] Un test vérifie que « Lancer » appelle `services/start` et affiche
      « Lancement… » jusqu'à l'apparition du projet dans l'inventaire

## Dépendances

Aucune.

## Ce que ça ne fait pas

- Ne relance pas une app lancée à la main avec sa commande d'origine :
  « Lancer » passe par les services déclarés dans `agents.json`.