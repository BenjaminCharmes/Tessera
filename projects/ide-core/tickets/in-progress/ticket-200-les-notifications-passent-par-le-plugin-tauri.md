---
id: ticket-200
title: "Les notifications passent par le plugin Tauri dans l'app desktop"
type: chore
status: in-progress
pr_number: null
priority: medium
agent: codeur
depends_on: ["ticket-192"]
estimated_days: 0.5
created: 2026-09-26
---

# ticket-200 — Les notifications passent par le plugin Tauri dans l'app desktop

## Objectif

Que les notifications du ticket-192 sortent aussi de l'app desktop, où la
WebView ne porte pas forcément l'API `Notification` du web.

## Contexte

Le ticket-192 a été livré avec l'API web seulement : aucune chaîne Rust
n'était disponible pour valider l'ajout d'un plugin par `cargo check`. La
chaîne est là depuis.

## Solution proposée

- `tauri-plugin-notification = "2"` dans `src-tauri/Cargo.toml`, enregistré
  dans le builder de `lib.rs`.
- La seule permission ajoutée : `notification:default` dans
  `capabilities/default.json`. Rien d'autre n'entre : ADR-040 tient.
- Paquet `@tauri-apps/plugin-notification` côté frontend. Le hook
  `useNotificationsSysteme` passe par le plugin quand il tourne dans Tauri
  (`isTauri()` de `@tauri-apps/api/core`), et garde l'API web ailleurs.
  Le plugin n'a pas de clic : la fenêtre ne se ramène pas au premier plan
  depuis une notification desktop, et c'est dit.

## Critères d'acceptation

- [ ] `capabilities/default.json` ne contient que `notification:default` en
      plus de l'existant
- [ ] `cargo check` passe dans `src-tauri`
- [ ] Un test vérifie que dans Tauri le hook appelle le plugin et pas
      `window.Notification`
- [ ] `npm run test`, `npm run typecheck`, `npm run build` passent

## Ce que ça ne fait pas

Pas de son, pas d'action sur la notification.

## Dépendances

ticket-192.

## Estimation

Une demi-journée.

## Risques

Le plugin demande la permission système à l'usage ; refusée, la
notification ne part pas et rien ne le dit à l'écran.
