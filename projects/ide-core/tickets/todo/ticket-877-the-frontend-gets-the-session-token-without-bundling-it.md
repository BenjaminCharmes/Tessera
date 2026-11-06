---
agent: codeur
created: 2026-11-06
depends_on: []
estimated_days: 1
id: ticket-877
pr_number: null
priority: critical
plan: true
status: todo
title: The frontend and the Tauri app get the API session token without bundling it
type: feat
---

# ticket-877 — Le frontend obtient le jeton de session sans le bundler

## Objectif

L'interface (navigateur en dev, app Tauri) sait porter un jeton de session
sur chaque requête et chaque WebSocket, sans que ce jeton soit jamais inscrit
dans le code servi par Vite. Premier de deux tickets : le backend
(ticket-878) ne l'exigera qu'une fois celui-ci livré, pour que l'interface ne
casse jamais.

## Contexte

Audit externe du 06/11 et design du jeton (ADR à venir, ticket-878). Un agent
avec `Bash` atteint l'API ouverte par `curl`. Le backend va exiger un jeton
tiré à chaque démarrage, écrit seulement dans
`ide_state_dir/jeton-de-session` (`%LOCALAPPDATA%\Tessera\` sous Windows,
`~/.local/state/tessera` ailleurs — voir `default_state_dir` dans
`backend/src/tessera/config.py`).

Aujourd'hui, `frontend/src/lib/auth.ts` lit `VITE_STATIC_TOKEN`, inliné par
Vite : en dev, `curl http://localhost:5173/src/lib/auth.ts` le rend à
n'importe quel processus local. Ce mécanisme disparaît.

## Solution proposée

- `frontend/src/lib/auth.ts` : `jetonDeSession()` cherche, dans l'ordre, la
  mémoire, `sessionStorage`, le fragment `#jeton=<t>` de l'URL (rangé en
  `sessionStorage`, puis effacé par `history.replaceState`), et, dans Tauri
  (`window.__TAURI_INTERNALS__`), `invoke("jeton_de_session")`, mis en cache.
  `authorized()` et `withTokenQuery()` gardent leur contrat. Plus aucune
  lecture de `VITE_STATIC_TOKEN` (retiré de `vite-env.d.ts`).
- `frontend/src/lib/http.ts` : une réponse 401 appelle un rappel
  `onJetonManquant`. Un composant `BandeauJeton` affiche alors un champ
  « Jeton de session » et le chemin du fichier ; la saisie va en
  `sessionStorage` et sert à la requête suivante.
- `frontend/src-tauri/src/lib.rs` : commande `#[tauri::command]
  jeton_de_session` qui lit le fichier (aucun plugin `fs`, ADR-040),
  enregistrée dans `invoke_handler`.
- `scripts/tessera.ps1` : après le démarrage du backend, lit le fichier s'il
  existe et affiche `http://localhost:5173/#jeton=<t>`.
- Le proxy Vite n'injecte **aucun** en-tête : il authentifierait tout client
  local de `:5173`, `curl` compris.

Les mises à jour des skills `run-tessera` et `verification-before-completion`
(dossier `.claude/`, interdit aux agents) se font à la main après le merge.

## Critères d'acceptation

- [ ] Un test de `frontend/src/lib/auth.test.ts` vérifie qu'avec
      `#jeton=abc` dans l'URL, `jetonDeSession()` rend `abc`,
      `sessionStorage` le porte et le fragment est vide ensuite.
- [ ] Un test de `auth.test.ts` vérifie qu'avec `window.__TAURI_INTERNALS__`
      présent, `invoke("jeton_de_session")` est appelé une seule fois pour
      deux lectures.
- [ ] Un test de `frontend/src/lib/http.test.ts` vérifie qu'une réponse 401
      appelle `onJetonManquant`, et qu'un jeton saisi ensuite est porté en
      `Authorization: Bearer` par la requête suivante.
- [ ] Un test de `frontend/src/lib/ws.test.ts` vérifie que l'URL de WebSocket
      porte `?token=` lu depuis `sessionStorage`.
- [ ] Le diff retire toute occurrence de `VITE_STATIC_TOKEN` de
      `frontend/src/` (sources et tests).
- [ ] `frontend/src-tauri/src/lib.rs` enregistre `jeton_de_session` dans
      `invoke_handler`.

## Dépendances

Aucune.

## Estimation

Une journée.

## Risques

`cargo` ne tourne pas sur ce poste (WDAC) : la partie Rust se vérifie dans
la CI de la PR `develop` → `main`. Garder la commande minimale.
