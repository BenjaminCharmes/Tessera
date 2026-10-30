---
id: ticket-721
title: "Stopped project tiles show the project icon"
type: fix
status: done
pr_number: null
priority: low
agent: codeur
depends_on: []
estimated_days: 0.1
created: 2026-10-30
---

# ticket-721 — Les tuiles des projets arrêtés montrent l'icône du projet

## Objectif
Reconnaître un projet arrêté d'un coup d'œil, à son icône.

## Contexte
Retour de Benjamin le 30/10 : les tuiles livrées par le ticket-710 portaient deux
barres grises identiques pour tous les projets.

## Fait
L'icône de la carte de la vue Projets devient `IconeDuProjet`, partagée, avec une
taille `tuile`. Comme sur la carte, un projet sans icône affiche son initiale.
Retouche à la main.

## Critères d'acceptation
- [x] `EnCoursArret.test.tsx` : la tuile d'un projet avec icône charge `/api/v1/projects/<id>/icon`, celle d'un projet sans icône affiche son initiale
