---
id: ticket-556
title: "Clicking a desktop notification brings Tessera forward and opens the project"
type: feat
status: todo
pr_number: null
priority: low
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-23
plan: true
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
- [ ] Le livrable dit, dans sa description de PR, quelle API du plugin donne le clic, ou qu'aucune ne le donne en 2.x
- [ ] Si l'API existe : un test, avec un double du plugin, montre qu'un clic appelle `ouvrir` avec le projet de la notification
- [ ] `src-tauri/capabilities/default.json` n'ouvre aucune permission `fs:*` ni `shell:*` (ADR-040)

## Risques
Rust se vérifie en CI seulement sur ce poste (WDAC) : une permission
Tauri ajoutée se valide par le job « Tauri (cargo check) ».
