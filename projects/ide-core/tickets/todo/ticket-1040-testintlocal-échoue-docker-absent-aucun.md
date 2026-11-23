---
agent: codeur
created: '2026-11-23'
depends_on: []
id: ticket-1040
priority: medium
status: todo
title: 'test:int:local échoue : Docker absent, aucun moyen de le démarrer'
type: fix
---

## Signalement

- Source : agent:codeur@ticket-215
- Nature : bug
- Projet source : kadoomi
- Catégorie : autre
- Composant : verification

## Description

Deux tours de suite, l'étape test:int:local échoue car le conteneur kadoomi-local-pg ne tourne pas. Le retour demande à l'agent de lancer « docker start », mais le démon Docker Desktop n'est pas démarré (pipe dockerDesktopLinuxEngine introuvable). L'agent ne peut pas corriger cela ; le ticket (bump better-auth) ne touche que package.json et le lockfile.

## Critères d'acceptation

- [ ] À écrire au triage