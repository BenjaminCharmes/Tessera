---
agent: codeur
created: 2026-10-23
depends_on: []
estimated_days: 0.5
id: ticket-556
plan: true
pr_number: null
priority: low
status: done
title: Clicking a desktop notification brings Tessera forward and opens the project
type: feat
---

# ticket-556 — Un clic sur une notification desktop ouvre le projet

## Objectif
Que cliquer une notification de l'app desktop fasse ce que fait déjà celle
du navigateur : ramener la fenêtre et ouvrir le projet.

## Contexte
`useNotificationsSysteme.ts` le dit : « Le plugin, lui, n'a pas de clic : la
fenêtre ne se ramène pas au premier plan depuis une notification desktop. »
Le projet est sur `@tauri-apps/plugin-notification` ^2.5.0. Le tour de plan
vérifie dans la documentation du plugin si une version 2.x expose un
événement de clic ou d'action (`onAction`) ; sinon, il le dit et le ticket
s'arrête au constat, noté dans `useNotificationsSysteme.ts`.

## Critères d'acceptation
- [x] Un commentaire de `useNotificationsSysteme.ts` dit quelle API du plugin donne le clic, ou qu'aucune ne le donne en 2.x
- [x] Sans objet : aucune API 2.x ne donne le clic desktop (`onAction` : « Only emitted on mobile », vérifié dans `@tauri-apps/plugin-notification` 2.5.0) ; un test vérifie que la branche Tauri n'appelle pas `ouvrir`
- [x] `src-tauri/capabilities/default.json` n'ouvre aucune permission `fs:*` ni `shell:*` (ADR-040)

## Risques
Rust se vérifie en CI seulement sur ce poste (WDAC) : une permission
Tauri ajoutée se valide par le job « Tauri (cargo check) ».

## Livraison du 23/10
Livré à la main : le validateur reconnaissait le constat à chaque tour mais
refusait le critère conditionnel « si l'API existe », sans objet ici.
