---
agent: codeur
created: '2026-11-23'
depends_on: []
id: ticket-1040
priority: medium
status: cancelled
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

## Annulé le 2026-11-24

Ce n'est pas un défaut de Tessera : la `test_command` de Kadoomi exige une base
Postgres dans Docker, et Docker Desktop n'était pas démarré. Décision du
24/11 : la fiche est annulée ici ; le message de `test:int:local` est corrigé
côté Kadoomi (son ticket-218) pour dire que le démon est arrêté et que le code
n'y peut rien, et Docker Desktop se lance à l'ouverture de session.