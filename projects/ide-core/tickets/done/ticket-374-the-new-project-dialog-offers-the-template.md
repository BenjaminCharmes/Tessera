---
agent: codeur
created: 2026-10-07
depends_on:
- ticket-373
estimated_days: 0.5
id: ticket-374
pr_number: null
priority: medium
status: done
title: The new-project dialog offers the FastAPI + React template and shows what is
  left to do by hand
type: feat
---

# ticket-374 — La fenêtre de création propose le gabarit FastAPI + React

## Objectif

Créer un projet depuis le gabarit sans quitter l'interface, et savoir ce qui
reste à faire à la main.

## Contexte

`frontend/src/components/Sidebar/CreateProjectModal.tsx` crée un projet
vide via `POST /api/v1/projects`. Le ticket-373 ajoute
`POST /api/v1/projects/from-template`, qui rend le projet, les ports
attribués et `git_ready`.

## Solution proposée

1. Dans `CreateProjectModal`, un choix « Projet vide » / « Gabarit FastAPI +
   React » ; le second appelle `api.projects.createFromTemplate`
   (`frontend/src/lib/api.ts`).
2. Après création depuis le gabarit, la fenêtre affiche les ports attribués
   (backend, frontend) et deux étapes restantes : écrire le `CLAUDE.md` du
   projet, créer le dépôt GitHub. Aucune action GitHub n'est lancée depuis
   cette fenêtre.

## Critères d'acceptation

- [ ] Un test de `frontend/src/components/Sidebar/CreateProjectModal.test.tsx` vérifie que le choix « Gabarit FastAPI + React » appelle `createFromTemplate` avec l'identifiant et le nom saisis, et pas la création de projet vide
- [ ] Un test de `frontend/src/components/Sidebar/CreateProjectModal.test.tsx` vérifie qu'après création, les ports rendus par l'API sont affichés
- [ ] Un test de `frontend/src/components/Sidebar/CreateProjectModal.test.tsx` vérifie que les étapes « écrire le CLAUDE.md » et « créer le dépôt GitHub » sont affichées après création
- [ ] Un test de `frontend/src/components/Sidebar/CreateProjectModal.test.tsx` vérifie que le choix « Projet vide » garde le comportement actuel

## Dépendances

ticket-373 (l'endpoint).

## Estimation

0,5 jour.

## Risques

Aucun pour la création de projet vide, inchangée.

## Ce que ça ne fait pas

- Ne crée pas le dépôt GitHub.
- N'édite pas le `CLAUDE.md`.