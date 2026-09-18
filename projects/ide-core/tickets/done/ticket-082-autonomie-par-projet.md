---
id: ticket-082
title: "Jusqu'où l'agent va se déclare par projet"
type: feat
status: done
pr_number: null
priority: high
agent: codeur
depends_on: [ticket-081]
estimated_days: 1
created: 2026-09-18
---

# ticket-082 — Jusqu'où l'agent va se déclare par projet

## Pourquoi

Deux besoins opposés, et une seule règle jusqu'ici.

Sur les dépôts pro, les accès sont souvent spécifiques : le travail se commite,
et l'utilisateur pousse lui-même une fois qu'il est prêt à le livrer. Un push
parti tout seul y serait une décision prise à sa place.

Sur `vibe-ide` et les projets personnels, c'est l'inverse : l'IDE doit pouvoir
tout mener — issue GitHub, commit, PR, tests, **et le merge**. Y exiger un clic
humain ne protège personne, ça freine.

ADR-022 tranchait « jamais de merge » pour tout le monde. Elle avait raison
pour le premier cas et tort pour le second.

## Objectif

Faire de la limite une déclaration du projet, pas une règle du produit, sur le
même patron qu'ADR-021 (artefacts) et ADR-028 (racine git) : **le défaut
protège, l'exception s'énonce**.

## Critères d'acceptation

- [x] `agents.json` accepte `autonomy` : `commit`, `pr` ou `merge`
- [x] Absent, illisible ou inconnu → `commit` (fail-closed)
- [x] Un run autonome ne pousse que si le projet le déclare
- [x] Le même geste demandé depuis l'IDE reste possible : le niveau borne ce
      que l'IDE fait **seul**
- [x] Le merge exige les deux conditions, vérifiées au moment d'agir : niveau
      `merge` **et** CI verte
- [x] `GitHubService.merge_pull_request` merge en merge commit, jamais en
      squash — `develop → main` garde l'historique par ticket
- [x] L'écran dit le niveau du projet, et propose le merge là où il vaut
- [x] ADR-029 écrite ; `ide-core` déclare `"autonomy": "merge"`

## Ce que ça ne fait pas

Le flux autonome de bout en bout (issue → ticket → run → PR → attente CI →
merge) n'est pas câblé : ce ticket pose la capacité et la porte, pas
l'enchaînement. La gestion des conflits reste à faire.
