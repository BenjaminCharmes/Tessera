---
id: ticket-140
title: "Projet : tableau de bord de santé des dépôts GitHub"
type: design
status: todo
pr_number: null
priority: low
agent: architect
depends_on: ["ticket-136"]
estimated_days: 1
created: 2026-09-23
---

# ticket-140 — Tableau de bord de santé des dépôts

## Objectif

Cadrer un projet construit par Tessera : voir d'un coup d'œil l'état de tous
ses dépôts — PR ouvertes, CI rouge, dépendances en retard, branches
orphelines.

## Contexte

Retenu parmi les candidats au projet from-scratch (ticket-136). Ce qu'il
apporte de spécifique à l'exercice : c'est le seul des trois qui exerce les
**appels d'API externes**, et donc le mocking — `respx` est déjà dans les
dépendances du backend, et `GitHubService` existe comme précédent (ADR-011,
httpx natif).

Il vient d'un besoin réel : cette session a laissé cinquante-deux branches
orphelines sur ce dépôt avant qu'on les nettoie, et il a fallu chercher
manuellement quelles PR empilées n'avaient pas déclenché leur CI.

## Solution proposée

À trancher au moment du cadrage :

1. Le périmètre — tous les dépôts d'un compte, ou une liste déclarée ?
2. Ce qu'on affiche : PR ouvertes et leur CI, branches sans PR, dépendances
   en retard (Dependabot), dernier commit par branche.
3. Le rafraîchissement : à la demande, ou périodique ? L'API GitHub a des
   quotas, et les brûler pour un tableau qu'on regarde deux fois par jour
   serait absurde.
4. Ce qui est stocké : rien du tout (tout se relit à chaque fois), ou un cache
   local pour tenir hors quota.
5. Le jeton : lu depuis l'environnement, jamais écrit dans le dépôt.

## Critères d'acceptation

- [ ] Les cinq questions ci-dessus ont une réponse écrite
- [ ] La décision dit ce qui se teste sans réseau, et ce qui exige un mock
- [ ] Le jeton GitHub n'apparaît dans aucun fichier versionné
- [ ] Le backlog initial est créé dans le projet, pas dans `ide-core`
- [ ] Le niveau d'`autonomy` du projet est arrêté (ADR-029)

## Dépendances

ticket-136, qui fixe ce qu'on observe pendant l'exercice.

## Estimation

1 jour de cadrage.

## Risques

Dépendre d'une API externe brouille la mesure : un run qui échoue parce que
GitHub a répondu 403 ne dit rien sur la qualité de l'orchestration. D'où la
question 5 du cadrage — ce qui se teste sans réseau doit être majoritaire.
