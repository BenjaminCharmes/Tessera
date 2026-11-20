---
agent: codeur
created: '2026-11-17'
depends_on: []
id: ticket-1002
priority: medium
status: cancelled
title: 'ci.yml illisible (EPERM) : documentation.test.ts échoue'
type: fix
---

## Signalement

- Source : agent:codeur@ticket-009
- Nature : bug
- Projet source : serpent
- Catégorie : outil_casse
- Composant : garde_perimetre

## Description

Dans le worktree ticket-009, ouvrir .github/workflows/ci.yml renvoie EPERM, même via Read. Le test « announces the Node version used by the CI » de src/documentation.test.ts échoue donc, sans lien avec le ticket. Il faut rendre le fichier lisible dans le worktree.

## Critères d'acceptation

- [ ] À écrire au triage

## Annulé le 18/11

Doublon du ticket-994 (mergé le 17/11), qui rend `ci.yml` lisible au compte
agent ; prouvé le 18/11 (Serpent 009 : 20 tests verts sous le compte).
Annulation décidée par Benjamin sur la page « À toi de jouer ».