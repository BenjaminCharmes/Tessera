---
id: ticket-602
title: "A window follows day and night, the director's office shows the employee of the week, and the door and the pile are shortcuts"
type: feat
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: ["ticket-597"]
estimated_days: 0.5
created: 2026-10-27
---

# ticket-602 — Fenêtre jour/nuit, employé de la semaine, porte et pile cliquables

## Objectif
Idées 5, 6 et 7 du « Bureau vivant » (`design/maquette/Bureau-vivant.dc.html`,
bouton de démo « Nuit », cadre dans le bureau du directeur, porte et pile
cliquables), validées le 27/10.

## Ce que dit la maquette
- **Fenêtre** au mur de chaque pièce (60 × 36 px) : ciel clair et soleil de
  7 h à 19 h (heure locale), ciel nuit et étoiles sinon ; la nuit, un voile
  sombre léger couvre la pièce. L'heure vient de l'horloge unique de la vue
  (`maintenant`), aucun minuteur de plus.
- **Employé de la semaine** : un cadre doré dans le bureau du directeur
  (ticket-597) avec le portrait du codeur (physique du ticket-595) du projet
  qui a le plus de tickets approuvés **au premier tour** sur les 7 derniers
  jours, et « <projet> · codeur, N tickets du 1er coup ». Source :
  `GET /api/v1/projects/{id}/runs` (`approved`, `rounds`, `started_at`). Aucun
  ticket approuvé au 1er tour sur la semaine : pas de cadre.
- **Raccourcis** : la porte d'une pièce est un bouton « Ouvrir le projet
  <nom> » qui choisit ce projet et ouvre l'onglet Tickets ; la pile de
  dossiers ouvre le fil du run (même action que le bouton « Fil »).

## Critères d'acceptation
- [ ] À 14 h la fenêtre rend `data-moment="jour"`, à 22 h `data-moment="nuit"` et le voile ; un test le vérifie avec une horloge injectée
- [ ] Avec deux projets, 3 et 5 tickets approuvés au 1er tour sur 7 jours, le cadre nomme le second et « 5 tickets du 1er coup » ; un test le vérifie
- [ ] Un ticket approuvé au tour 2, ou il y a 8 jours, ne compte pas ; un test le vérifie
- [ ] Sans ticket approuvé au 1er tour sur la semaine, aucun cadre n'est rendu ; un test le vérifie
- [ ] Un clic sur la porte choisit le projet et ouvre l'onglet Tickets ; un test le vérifie avec des doubles
- [ ] Un clic sur la pile appelle la même ouverture de fil que le bouton « Fil » ; un test le vérifie
- [ ] Le diff ne modifie aucun fichier de `backend/`
